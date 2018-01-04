## Copyright (C) University of Tennessee Health Science Center, Memphis, TN.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# This program is available from Source Forge: at GeneNetwork Project
# (sourceforge.net/projects/genenetwork/).
#
# Contact Dr. Robert W. Williams at rwilliams@uthsc.edu
#
#
# This module is used by GeneNetwork project (www.genenetwork.org)

from __future__ import absolute_import, print_function, division

import sys
# sys.path.append(".") Never in a running webserver

import gc
import string
import cPickle
import os
import time
import pp
import math
import collections
import resource

import scipy

from pprint import pformat as pf

from htmlgen import HTMLgen2 as HT
import reaper

from base import webqtlConfig
from utility.THCell import THCell
from utility.TDCell import TDCell
from base.trait import GeneralTrait
from base import data_set
from utility import webqtlUtil, helper_functions, corr_result_helpers
from db import webqtlDatabaseFunction
import utility.webqtlUtil #this is for parallel computing only.
from wqflask.correlation import correlation_functions
from utility.benchmark import Bench
import utility.webqtlUtil

from MySQLdb import escape_string as escape

from pprint import pformat as pf

from flask import Flask, g

import utility.logger
logger = utility.logger.getLogger(__name__ )

METHOD_SAMPLE_PEARSON = "1"
METHOD_SAMPLE_RANK = "2"
METHOD_LIT = "3"
METHOD_TISSUE_PEARSON = "4"
METHOD_TISSUE_RANK = "5"

TISSUE_METHODS = [METHOD_TISSUE_PEARSON, METHOD_TISSUE_RANK]

TISSUE_MOUSE_DB = 1

def print_mem(stage=""):
    mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    #print("{}: {}".format(stage, mem/1024))


class AuthException(Exception):
    pass

class CorrelationResults(object):

    corr_min_informative = 4

    #PAGE_HEADING = "Correlation Table"
    #CORRELATION_METHODS = {"1" : "Genetic Correlation (Pearson's r)",
    #                       "2" : "Genetic Correlation (Spearman's rho)",
    #                       "3" : "SGO Literature Correlation",
    #                       "4" : "Tissue Correlation (Pearson's r)",
    #                       "5" : "Tissue Correlation (Spearman's rho)"}
    #
    #RANK_ORDERS = {"1": 0, "2": 1, "3": 0, "4": 0, "5": 1}

    def __init__(self, start_vars):
        # get trait list from db (database name)
        # calculate correlation with Base vector and targets

        print("TESTING...")

        with Bench("Doing correlations"):
            if start_vars['dataset'] == "Temp":
                self.dataset = data_set.create_dataset(dataset_name = "Temp", dataset_type = "Temp", group_name = start_vars['group'])
                self.trait_id = "Temp"
                self.this_trait = GeneralTrait(dataset=self.dataset,
                                           name=self.trait_id,
                                           cellid=None)
            else:
                helper_functions.get_species_dataset_trait(self, start_vars)

            self.dataset.group.read_genotype_file()

            corr_samples_group = start_vars['corr_samples_group']

            self.sample_data = {}
            self.corr_type = start_vars['corr_type']
            self.corr_method = start_vars['corr_sample_method']
            if 'min_expr' in start_vars:
                if start_vars['min_expr'] != "":
                    self.min_expr = float(start_vars['min_expr'])
                else:
                    self.min_expr = None
            self.p_range_lower = float(start_vars['p_range_lower'])
            self.p_range_upper = float(start_vars['p_range_upper'])

            if ('loc_chr' in start_vars and
                'min_loc_mb' in start_vars and
                'max_loc_mb' in start_vars):

                self.location_chr = start_vars['loc_chr']
                if start_vars['min_loc_mb'].isdigit():
                    self.min_location_mb = start_vars['min_loc_mb']
                else:
                    self.min_location_mb = None
                if start_vars['max_loc_mb'].isdigit():
                    self.max_location_mb = start_vars['max_loc_mb']
                else:
                    self.max_location_mb = None

            self.get_formatted_corr_type()
            self.return_number = int(start_vars['corr_return_results'])

            #The two if statements below append samples to the sample list based upon whether the user
            #rselected Primary Samples Only, Other Samples Only, or All Samples

            primary_samples = self.dataset.group.samplelist
            if self.dataset.group.parlist != None:
                primary_samples += self.dataset.group.parlist
            if self.dataset.group.f1list != None:
                primary_samples += self.dataset.group.f1list

            #If either BXD/whatever Only or All Samples, append all of that group's samplelist
            if corr_samples_group != 'samples_other':
                self.process_samples(start_vars, primary_samples)

            #If either Non-BXD/whatever or All Samples, get all samples from this_trait.data and
            #exclude the primary samples (because they would have been added in the previous
            #if statement if the user selected All Samples)
            if corr_samples_group != 'samples_primary':
                if corr_samples_group == 'samples_other':
                    primary_samples = [x for x in primary_samples if x not in (
                                    self.dataset.group.parlist + self.dataset.group.f1list)]
                self.process_samples(start_vars, self.this_trait.data.keys(), primary_samples)

            self.target_dataset = data_set.create_dataset(start_vars['corr_dataset'])
            # print("self.sample_data.keys: %s" % self.sample_data.keys)
            self.target_dataset.get_trait_data(self.sample_data.keys())

            self.correlation_results = []

            self.correlation_data = {}

            db_filename = self.getFileName(target_db_name = self.target_dataset.name)
            cache_available = db_filename in os.listdir(webqtlConfig.GENERATED_TEXT_DIR)

            if self.corr_type == "tissue":
                self.trait_symbol_dict = self.dataset.retrieve_genes("Symbol")

                tissue_corr_data = self.do_tissue_correlation_for_all_traits()
                if tissue_corr_data != None:
                    for trait in tissue_corr_data.keys()[:self.return_number]:
                        self.get_sample_r_and_p_values(trait, self.target_dataset.trait_data[trait])
                else:
                    for trait, values in self.target_dataset.trait_data.iteritems():
                        self.get_sample_r_and_p_values(trait, values)
                        
            elif self.corr_type == "lit":
                self.trait_geneid_dict = self.dataset.retrieve_genes("GeneId")
                lit_corr_data = self.do_lit_correlation_for_all_traits()

                for trait in lit_corr_data.keys()[:self.return_number]:
                    self.get_sample_r_and_p_values(trait, self.target_dataset.trait_data[trait])

            elif self.corr_type == "sample":
                if self.dataset.type == "ProbeSet" and cache_available:
                    dataset_file = open(webqtlConfig.GENERATED_TEXT_DIR+db_filename,'r')

                    #XZ, 01/08/2009: read the first line
                    line = dataset_file.readline()
                    dataset_strains = webqtlUtil.readLineCSV(line)[1:]

                    self.this_trait_vals = []
                    for item in dataset_strains:
                        if item in self.sample_data:
                            self.this_trait_vals.append(self.sample_data[item])
                        else:
                            self.this_trait_vals.append("None")
                    num_overlap = len(self.this_trait_vals)

                    self.do_parallel_correlation(db_filename, num_overlap)
                else:
                    for trait, values in self.target_dataset.trait_data.iteritems():
                        self.get_sample_r_and_p_values(trait, values)

                self.correlation_data = collections.OrderedDict(sorted(self.correlation_data.items(),
                                                                       key=lambda t: -abs(t[1][0])))


            if self.target_dataset.type == "ProbeSet" or self.target_dataset.type == "Geno":
                #ZS: Convert min/max chromosome to an int for the location range option
                range_chr_as_int = None
                for order_id, chr_info in self.dataset.species.chromosomes.chromosomes.iteritems():
                    if chr_info.name == self.location_chr:
                        range_chr_as_int = order_id

            for _trait_counter, trait in enumerate(self.correlation_data.keys()[:self.return_number]):
                trait_object = GeneralTrait(dataset=self.target_dataset, name=trait, get_qtl_info=True, get_sample_info=False)

                if self.target_dataset.type == "ProbeSet" or self.target_dataset.type == "Geno":
                    #ZS: Convert trait chromosome to an int for the location range option
                    chr_as_int = 0
                    for order_id, chr_info in self.dataset.species.chromosomes.chromosomes.iteritems():
                        if chr_info.name == trait_object.chr:
                            chr_as_int = order_id

                if (float(self.correlation_data[trait][0]) >= self.p_range_lower and
                    float(self.correlation_data[trait][0]) <= self.p_range_upper):

                    if self.target_dataset.type == "ProbeSet" or self.target_dataset.type == "Geno":

                        if (self.min_expr != None) and (float(trait_object.mean) < self.min_expr):
                            continue
                        elif range_chr_as_int != None and (chr_as_int != range_chr_as_int):
                            continue
                        elif (self.min_location_mb != None) and (float(trait_object.mb) < float(self.min_location_mb)):
                            continue
                        elif (self.max_location_mb != None) and (float(trait_object.mb) > float(self.max_location_mb)):
                            continue

                        (trait_object.sample_r,
                        trait_object.sample_p,
                        trait_object.num_overlap) = self.correlation_data[trait]

                        #Get symbol for trait and call function that gets each tissue value from the database (tables TissueProbeSetXRef,
                        #TissueProbeSetData, etc) and calculates the correlation (cal_zero_order_corr_for_tissue in correlation_functions)

                        # Set some sane defaults
                        trait_object.tissue_corr = 0
                        trait_object.tissue_pvalue = 0
                        trait_object.lit_corr = 0
                        if self.corr_type == "tissue" and tissue_corr_data != None:
                            trait_object.tissue_corr = tissue_corr_data[trait][1]
                            trait_object.tissue_pvalue = tissue_corr_data[trait][2]
                        elif self.corr_type == "lit":
                            trait_object.lit_corr = lit_corr_data[trait][1]
                        self.correlation_results.append(trait_object)
                    else:
                        (trait_object.sample_r,
                        trait_object.sample_p,
                        trait_object.num_overlap) = self.correlation_data[trait]

                        #Get symbol for trait and call function that gets each tissue value from the database (tables TissueProbeSetXRef,
                        #TissueProbeSetData, etc) and calculates the correlation (cal_zero_order_corr_for_tissue in correlation_functions)

                        # Set some sane defaults
                        trait_object.tissue_corr = 0
                        trait_object.tissue_pvalue = 0
                        trait_object.lit_corr = 0
                        if self.corr_type == "tissue":
                            trait_object.tissue_corr = tissue_corr_data[trait][1]
                            trait_object.tissue_pvalue = tissue_corr_data[trait][2]
                        elif self.corr_type == "lit":
                            trait_object.lit_corr = lit_corr_data[trait][1]
                        self.correlation_results.append(trait_object)

            self.target_dataset.get_trait_info(self.correlation_results, self.target_dataset.group.species)

            if self.corr_type != "lit" and self.dataset.type == "ProbeSet" and self.target_dataset.type == "ProbeSet":
                self.do_lit_correlation_for_trait_list()

            if self.corr_type != "tissue" and self.dataset.type == "ProbeSet" and self.target_dataset.type == "ProbeSet":
                self.do_tissue_correlation_for_trait_list()

            #print("self.correlation_results: ", pf(self.correlation_results))


        #XZ, 09/18/2008: get all information about the user selected database.
        #target_db_name = fd.corr_dataset
        #self.target_db_name = start_vars['corr_dataset']

        # Zach said this is ok
        # Auth if needed
        #try:
        #    auth_user_for_db(self.db, self.cursor, self.target_db_name, self.privilege, self.userName)
        #except AuthException as e:
        #    detail = [e.message]
        #    return self.error(detail)

        #XZ, 09/18/2008: filter out the strains that have no value.
        #self.sample_names, vals, vars, N = fd.informativeStrains(sample_list)

        #print("samplenames is:", pf(self.sample_names))
        #CF - If less than a minimum number of strains/cases in common, don't calculate anything
        #if len(self.sample_names) < self.corr_min_informative:
        #    detail = ['Fewer than %d strain data were entered for %s data set. No calculation of correlation has been attempted.' % (self.corr_min_informative, fd.RISet)]
        #    self.error(heading=None, detail=detail)

        #correlation_method = self.CORRELATION_METHODS[self.method]
        #rankOrder = self.RANK_ORDERS[self.method]

        # CF - Number of results returned
        # Todo: Get rid of self.returnNumber

        #self.record_count = 0

        #myTrait = get_custom_trait(fd, self.cursor)


        # We will not get Literature Correlations if there is no GeneId because there is nothing
        # to look against
        #self.geneid = self.this_trait.geneid

        # We will not get Tissue Correlations if there is no gene symbol because there is nothing to look against
        #self.trait_symbol = myTrait.symbol


        #XZ, 12/12/2008: if the species is rat or human, translate the geneid to mouse geneid
        #self.input_trait_mouse_gene_id = self.translateToMouseGeneID(self.dataset.group.species, self.geneid)

        #XZ: As of Nov/13/2010, this dataset is 'UTHSC Illumina V6.2 RankInv B6 D2 average CNS GI average (May 08)'
        #self.tissue_probeset_freeze_id = 1

        #traitList = self.correlate()

        #print("Done doing correlation calculation")

############################################################################################################################################

    def get_formatted_corr_type(self):
        self.formatted_corr_type = ""
        if self.corr_type == "lit":
            self.formatted_corr_type += "Literature Correlation "
        elif self.corr_type == "tissue":
            self.formatted_corr_type += "Tissue Correlation "
        elif self.corr_type == "sample":
            self.formatted_corr_type += "Genetic Correlation "

        if self.corr_method == "pearson":
            self.formatted_corr_type += "(Pearson's r)"
        elif self.corr_method == "spearman":
            self.formatted_corr_type += "(Spearman's rho)"

    def do_tissue_correlation_for_trait_list(self, tissue_dataset_id=1):
        """Given a list of correlation results (self.correlation_results), gets the tissue correlation value for each"""

        #Gets tissue expression values for the primary trait
        primary_trait_tissue_vals_dict = correlation_functions.get_trait_symbol_and_tissue_values(
            symbol_list = [self.this_trait.symbol])

        if self.this_trait.symbol.lower() in primary_trait_tissue_vals_dict:
            primary_trait_tissue_values = primary_trait_tissue_vals_dict[self.this_trait.symbol.lower()]

            #gene_symbol_list = []
            #
            #for trait in self.correlation_results:
            #    if hasattr(trait, 'symbol'):
            #        gene_symbol_list.append(trait.symbol)

            gene_symbol_list = [trait.symbol for trait in self.correlation_results if trait.symbol]

            corr_result_tissue_vals_dict= correlation_functions.get_trait_symbol_and_tissue_values(
                                                    symbol_list=gene_symbol_list)

            for trait in self.correlation_results:
                if trait.symbol and trait.symbol.lower() in corr_result_tissue_vals_dict:
                    this_trait_tissue_values = corr_result_tissue_vals_dict[trait.symbol.lower()]

                    result = correlation_functions.cal_zero_order_corr_for_tiss(primary_trait_tissue_values,
                                                                          this_trait_tissue_values,
                                                                          self.corr_method)

                    trait.tissue_corr = result[0]
                    trait.tissue_pvalue = result[2]

        #        else:
        #            trait.tissue_corr = None
        #            trait.tissue_pvalue = None
        #else:
        #    for trait in self.correlation_results:
        #        trait.tissue_corr = None
        #        trait.tissue_pvalue = None

        #return self.correlation_results


    def do_tissue_correlation_for_all_traits(self, tissue_dataset_id=1):
        #Gets tissue expression values for the primary trait
        primary_trait_tissue_vals_dict = correlation_functions.get_trait_symbol_and_tissue_values(
            symbol_list = [self.this_trait.symbol])

        if self.this_trait.symbol.lower() in primary_trait_tissue_vals_dict:
            primary_trait_tissue_values = primary_trait_tissue_vals_dict[self.this_trait.symbol.lower()]

            #print("trait_gene_symbols: ", pf(trait_gene_symbols.values()))
            corr_result_tissue_vals_dict= correlation_functions.get_trait_symbol_and_tissue_values(
                                                    symbol_list=self.trait_symbol_dict.values())

            #print("corr_result_tissue_vals: ", pf(corr_result_tissue_vals_dict))

            #print("trait_gene_symbols: ", pf(trait_gene_symbols))

            tissue_corr_data = {}
            for trait, symbol in self.trait_symbol_dict.iteritems():
                if symbol and symbol.lower() in corr_result_tissue_vals_dict:
                    this_trait_tissue_values = corr_result_tissue_vals_dict[symbol.lower()]
                    #print("this_trait_tissue_values: ", pf(this_trait_tissue_values))

                    result = correlation_functions.cal_zero_order_corr_for_tiss(primary_trait_tissue_values,
                                                                          this_trait_tissue_values,
                                                                          self.corr_method)

                    tissue_corr_data[trait] = [symbol, result[0], result[2]]

            tissue_corr_data = collections.OrderedDict(sorted(tissue_corr_data.items(),
                                                           key=lambda t: -abs(t[1][1])))

            return tissue_corr_data


    def do_lit_correlation_for_trait_list(self):

        input_trait_mouse_gene_id = self.convert_to_mouse_gene_id(self.dataset.group.species.lower(), self.this_trait.geneid)

        for trait in self.correlation_results:

            if trait.geneid:
                trait.mouse_gene_id = self.convert_to_mouse_gene_id(self.dataset.group.species.lower(), trait.geneid)
            else:
                trait.mouse_gene_id = None

            if trait.mouse_gene_id and str(trait.mouse_gene_id).find(";") == -1:
                result = g.db.execute(
                    """SELECT value
                       FROM LCorrRamin3
                       WHERE GeneId1='%s' and
                             GeneId2='%s'
                    """ % (escape(str(trait.mouse_gene_id)), escape(str(input_trait_mouse_gene_id)))
                ).fetchone()
                if not result:
                    result = g.db.execute("""SELECT value
                       FROM LCorrRamin3
                       WHERE GeneId2='%s' and
                             GeneId1='%s'
                    """ % (escape(str(trait.mouse_gene_id)), escape(str(input_trait_mouse_gene_id)))
                    ).fetchone()

                if result:
                    lit_corr = result.value
                    trait.lit_corr = lit_corr
                else:
                    trait.lit_corr = 0
            else:
                trait.lit_corr = 0


    def do_lit_correlation_for_all_traits(self):
        input_trait_mouse_gene_id = self.convert_to_mouse_gene_id(self.dataset.group.species.lower(), self.this_trait.geneid)

        lit_corr_data = {}
        for trait, gene_id in self.trait_geneid_dict.iteritems():
            mouse_gene_id = self.convert_to_mouse_gene_id(self.dataset.group.species.lower(), gene_id)

            if mouse_gene_id and str(mouse_gene_id).find(";") == -1:
                #print("gene_symbols:", input_trait_mouse_gene_id + " / " + mouse_gene_id)
                result = g.db.execute(
                    """SELECT value
                       FROM LCorrRamin3
                       WHERE GeneId1='%s' and
                             GeneId2='%s'
                    """ % (escape(mouse_gene_id), escape(input_trait_mouse_gene_id))
                ).fetchone()
                if not result:
                    result = g.db.execute("""SELECT value
                       FROM LCorrRamin3
                       WHERE GeneId2='%s' and
                             GeneId1='%s'
                    """ % (escape(mouse_gene_id), escape(input_trait_mouse_gene_id))
                    ).fetchone()
                if result:
                    #print("result:", result)
                    lit_corr = result.value
                    lit_corr_data[trait] = [gene_id, lit_corr]
                else:
                    lit_corr_data[trait] = [gene_id, 0]
            else:
                lit_corr_data[trait] = [gene_id, 0]

        lit_corr_data = collections.OrderedDict(sorted(lit_corr_data.items(),
                                                           key=lambda t: -abs(t[1][1])))

        return lit_corr_data

    def convert_to_mouse_gene_id(self, species=None, gene_id=None):
        """If the species is rat or human, translate the gene_id to the mouse geneid

        If there is no input gene_id or there's no corresponding mouse gene_id, return None

        """
        if not gene_id:
            return None

        mouse_gene_id = None

        if species == 'mouse':
            mouse_gene_id = gene_id

        elif species == 'rat':

            query = """SELECT mouse
                   FROM GeneIDXRef
                   WHERE rat='%s'""" % escape(gene_id)

            result = g.db.execute(query).fetchone()
            if result != None:
                mouse_gene_id = result.mouse

        elif species == 'human':

            query = """SELECT mouse
                   FROM GeneIDXRef
                   WHERE human='%s'""" % escape(gene_id)

            result = g.db.execute(query).fetchone()
            if result != None:
                mouse_gene_id = result.mouse

        return mouse_gene_id

    def get_sample_r_and_p_values(self, trait, target_samples):
        """Calculates the sample r (or rho) and p-value

        Given a primary trait and a target trait's sample values,
        calculates either the pearson r or spearman rho and the p-value
        using the corresponding scipy functions.

        """

        self.this_trait_vals = []
        target_vals = []
        for index, sample in enumerate(self.target_dataset.samplelist):
            if sample in self.sample_data:
                sample_value = self.sample_data[sample]
                target_sample_value = target_samples[index]
                self.this_trait_vals.append(sample_value)
                target_vals.append(target_sample_value)

        self.this_trait_vals, target_vals, num_overlap = corr_result_helpers.normalize_values(self.this_trait_vals, target_vals)	

        #ZS: 2015 could add biweight correlation, see http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3465711/
        if self.corr_method == 'pearson':
            sample_r, sample_p = scipy.stats.pearsonr(self.this_trait_vals, target_vals)
        else:
            sample_r, sample_p = scipy.stats.spearmanr(self.this_trait_vals, target_vals)

        if num_overlap > 5:
            self.correlation_data[trait] = [sample_r, sample_p, num_overlap]
		
		
        """
        correlations = []

        #XZ: Use the fast method only for probeset dataset, and this dataset must have been created.
        #XZ: Otherwise, use original method
        #print("Entering correlation")

        #db_filename = self.getFileName(target_db_name=self.target_db_name)
        #
        #cache_available = db_filename in os.listdir(webqtlConfig.GENERATED_TEXT_DIR)

         # If the cache file exists, do a cached correlation for probeset data
        if self.dataset.type == "ProbeSet":
#           if self.method in [METHOD_SAMPLE_PEARSON, METHOD_SAMPLE_RANK] and cache_available:
#               traits = do_parallel_correlation()
#
#           else:

            traits = self.get_traits(self.vals)

            for trait in traits:
                trait.calculate_correlation(vals, self.method)

        self.record_count = len(traits) #ZS: This isn't a good way to get this value, so I need to change it later

        #XZ, 3/31/2010: Theoretically, we should create one function 'comTissueCorr'
        #to compare each trait by their tissue corr p values.
        #But because the tissue corr p values are generated by permutation test,
        #the top ones always have p value 0. So comparing p values actually does nothing.
        #In addition, for the tissue data in our database, the N is always the same.
        #So it's safe to compare with tissue corr statistic value.
        #That's the same as literature corr.
        #if self.method in [METHOD_LIT, METHOD_TISSUE_PEARSON, METHOD_TISSUE_RANK] and self.gene_id:
        #    traits.sort(webqtlUtil.cmpLitCorr)
        #else:
        #if self.method in TISSUE_METHODS:
        #    sort(traits, key=lambda A: math.fabs(A.tissue_corr))
        #elif self.method == METHOD_LIT:
        #    traits.sort(traits, key=lambda A: math.fabs(A.lit_corr))
        #else:
        traits = sortTraitCorrelations(traits, self.method)

        # Strip to the top N correlations
        traits = traits[:min(self.returnNumber, len(traits))]

        addLiteratureCorr = False
        addTissueCorr = False

        trait_list = []
        for trait in traits:
            db_trait = webqtlTrait(db=self.db, name=trait.name, cursor=self.cursor)
            db_trait.retrieveInfo( QTL='Yes' )

            db_trait.Name = trait.name
            db_trait.corr = trait.correlation
            db_trait.nOverlap = trait.overlap
            db_trait.corrPValue = trait.p_value

            # NL, 07/19/2010
            # js function changed, add a new parameter rankOrder for js function 'showTissueCorrPlot'
            db_trait.RANK_ORDER = self.RANK_ORDERS[self.method]

            #XZ, 26/09/2008: Method is 4 or 5. Have fetched tissue corr, but no literature correlation yet.
            if self.method in TISSUE_METHODS:
                db_trait.tissueCorr = trait.tissue_corr
                db_trait.tissuePValue = trait.p_tissue
                addTissueCorr = True


            #XZ, 26/09/2008: Method is 3,  Have fetched literature corr, but no tissue corr yet.
            elif self.method == METHOD_LIT:
                db_trait.LCorr = trait.lit_corr
                db_trait.mouse_geneid = self.translateToMouseGeneID(self.species, db_trait.geneid)
                addLiteratureCorr = True

            #XZ, 26/09/2008: Method is 1 or 2. Have NOT fetched literature corr and tissue corr yet.
            # Phenotype data will not have geneid, and neither will some probes
            # we need to handle this because we will get an attribute error
            else:
                if self.input_trait_mouse_gene_id and self.db.type=="ProbeSet":
                    addLiteratureCorr = True
                if self.trait_symbol and self.db.type=="ProbeSet":
                    addTissueCorr = True

            trait_list.append(db_trait)

        if addLiteratureCorr:
            trait_list = self.getLiteratureCorrelationByList(self.input_trait_mouse_gene_id,
                                                    self.species, trait_list)
        if addTissueCorr:
            trait_list = self.getTissueCorrelationByList(
                        primaryTraitSymbol = self.trait_symbol,
                        traitList = trait_list,
                        TissueProbeSetFreezeId = TISSUE_MOUSE_DB,
                        method=self.method)

        return trait_list
        """		
		

    def do_tissue_corr_for_all_traits_2(self):
        """Comments Possibly Out of Date!!!!!

        Uses get_temp_tissue_corr_table to generate table of tissue correlations

        This function then gathers that data and pairs it with the TraitID string.
        Takes as its arguments a formdata instance, and a dataset instance.
        Returns a dictionary of 'TraitID':(tissueCorr, tissuePValue)
        for the requested correlation

        Used when the user selects the tissue correlation method; i.e. not for the
        column that is appended to all probeset trait correlation tables

        """

        # table name string
        temp_table = self.get_temp_tissue_corr_table(tissue_probesetfreeze_id=TISSUE_MOUSE_DB,
                                                    method=method)

        query = """SELECT ProbeSet.Name, {}.Correlation, {}.PValue
                FROM (ProbeSet, ProbeSetXRef, ProbeSetFreeze)
                LEFT JOIN {} ON {}.Symbol=ProbeSet.Symbol
                WHERE ProbeSetFreeze.Name = '{}'
                and ProbeSetFreeze.Id=ProbeSetXRef.ProbeSetFreezeId
                and ProbeSet.Id = ProbeSetXRef.ProbeSetId
                and ProbeSet.Symbol IS NOT NULL
                and {}.Correlation IS NOT NULL""".format(dataset.mescape(
                    temp_table, temp_table, temp_table, temp_table,
                    self.dataset.name, temp_table))

        results = g.db.execute(query).fetchall()

        tissue_corr_dict = {}

        for entry in results:
            trait_name, tissue_corr, tissue_pvalue = entry
            tissue_corr_dict[trait_name] = (tissue_corr, tissue_pvalue)
    #symbolList,
    #geneIdDict,
    #dataIdDict,
    #ChrDict,
    #MbDict,
    #descDict,
    #pTargetDescDict = getTissueProbeSetXRefInfo(
    #                    GeneNameLst=GeneNameLst,TissueProbeSetFreezeId=TissueProbeSetFreezeId)

        g.db.execute('DROP TEMPORARY TABLE {}'.format(escape(temp_table)))

        return tissue_corr_dict


    #XZ, 09/23/2008: In tissue correlation tables, there is no record of GeneId1 == GeneId2
    #XZ, 09/24/2008: Note that the correlation value can be negative.
    def get_temp_tissue_corr_table(self,
                                   tissue_probesetfreeze_id=0,
                                   method="",
                                   return_number=0):


        def cmp_tisscorr_absolute_value(A, B):
            try:
                if abs(A[1]) < abs(B[1]): return 1
                elif abs(A[1]) == abs(B[1]):
                    return 0
                else: return -1
            except:
                return 0

        symbol_corr_dict, symbol_pvalue_dict = self.calculate_corr_for_all_tissues(
                                                                tissue_dataset_id=TISSUE_MOUSE_DB)

        symbol_corr_list = symbol_corr_dict.items()

        symbol_corr_list.sort(cmp_tisscorr_absolute_value)
        symbol_corr_list = symbol_corr_list[0 : 2*return_number]

        tmp_table_name = webqtlUtil.genRandStr(prefix="TOPTISSUE")

        q1 = 'CREATE TEMPORARY TABLE %s (Symbol varchar(100) PRIMARY KEY, Correlation float, PValue float)' % tmp_table_name
        self.cursor.execute(q1)

        for one_pair in symbol_corr_list:
            one_symbol = one_pair[0]
            one_corr = one_pair[1]
            one_p_value = symbol_pvalue_dict[one_symbol]

            self.cursor.execute( "INSERT INTO %s (Symbol, Correlation, PValue) VALUES ('%s',%f,%f)" % (tmpTableName, one_symbol, float(one_corr), float(one_p_value)) )

        return tmp_table_name


    def calculate_corr_for_all_tissues(self, tissue_dataset_id=None):

        symbol_corr_dict = {}
        symbol_pvalue_dict = {}

        primary_trait_symbol_value_dict = correlation_functions.make_gene_tissue_value_dict(
                                                    GeneNameLst=[self.this_trait.symbol],
                                                    TissueProbeSetFreezeId=tissue_dataset_id)
        primary_trait_value = primary_trait_symbol_value_dict.values()[0]

        symbol_value_dict = correlation_functions.make_gene_tissue_value_dict(
                                        gene_name_list=[],
                                        tissue_dataset_id=tissue_dataset_id)

        symbol_corr_dict, symbol_pvalue_dict = correlation_functions.batch_cal_tissue_corr(
                primaryTraitValue,
                SymbolValueDict,
                method=self.corr_method)
        #else:
        #    symbol_corr_dict, symbol_pvalue_dict = correlation_functions.batch_cal_tissue_corr(
        #        primaryTraitValue,
        #        SymbolValueDict)

        return (symbolCorrDict, symbolPvalueDict)

    ##XZ, 12/16/2008: the input geneid is of mouse type
    #def checkSymbolForTissueCorr(self, tissueProbeSetFreezeId=0, symbol=""):
    #    q = "SELECT 1 FROM  TissueProbeSetXRef WHERE TissueProbeSetFreezeId=%s and Symbol='%s' LIMIT 1" % (tissueProbeSetFreezeId,symbol)
    #    self.cursor.execute(q)
    #    try:
    #        x = self.cursor.fetchone()
    #        if x: return True
    #        else: raise
    #    except: return False


    def process_samples(self, start_vars, sample_names, excluded_samples=None):
        if not excluded_samples:
            excluded_samples = ()

        for sample in sample_names:
            if sample not in excluded_samples:
                # print("Looking for",sample,"in",start_vars)
                value = start_vars.get('value:' + sample)
                if value:
                    if not value.strip().lower() == 'x':
                        self.sample_data[str(sample)] = float(value)

    ##XZ, 12/16/2008: the input geneid is of mouse type
    #def checkForLitInfo(self,geneId):
    #    q = 'SELECT 1 FROM LCorrRamin3 WHERE GeneId1=%s LIMIT 1' % geneId
    #    self.cursor.execute(q)
    #    try:
    #        x = self.cursor.fetchone()
    #        if x: return True
    #        else: raise
    #    except: return False



    def fetchAllDatabaseData(self, species, GeneId, GeneSymbol, strains, db, method, returnNumber, tissueProbeSetFreezeId):

        StrainIds = []
        for item in strains:
            self.cursor.execute('''SELECT Strain.Id FROM Strain, Species WHERE Strain.Name="%s" and Strain.SpeciesId=Species.Id and Species.name = "%s" ''' % (item, species))
            Id = self.cursor.fetchone()[0]
            StrainIds.append('%d' % Id)

        # break it into smaller chunks so we don't overload the MySql server
        nnn = len(StrainIds) / 25
        if len(StrainIds) % 25:
            nnn += 1
        oridata = []

        #XZ, 09/24/2008: build one temporary table that only contains the records associated with the input GeneId
        tempTable = None
        if GeneId and db.type == "ProbeSet":
            if method == "3":
                tempTable = self.getTempLiteratureTable(species=species, input_species_geneid=GeneId, returnNumber=returnNumber)

            if method == "4" or method == "5":
                tempTable = self.getTempTissueCorrTable(primaryTraitSymbol=GeneSymbol, TissueProbeSetFreezeId=TISSUE_MOUSE_DB, method=method, returnNumber=returnNumber)

        for step in range(nnn):
            temp = []
            StrainIdstep = StrainIds[step*25:min(len(StrainIds), (step+1)*25)]
            for item in StrainIdstep: temp.append('T%s.value' % item)

            if db.type == "Publish":
                query = "SELECT PublishXRef.Id, "
                dataStartPos = 1
                query += string.join(temp,', ')
                query += ' FROM (PublishXRef, PublishFreeze)'
                #XZ, 03/04/2009: Xiaodong changed Data to PublishData
                for item in StrainIdstep:
                    query += 'left join PublishData as T%s on T%s.Id = PublishXRef.DataId and T%s.StrainId=%s\n' %(item,item,item,item)
                query += "WHERE PublishXRef.InbredSetId = PublishFreeze.InbredSetId and PublishFreeze.Name = '%s'" % (db.name, )
            #XZ, 09/20/2008: extract literature correlation value together with gene expression values.
            #XZ, 09/20/2008: notice the difference between the code in next block.
            #elif tempTable:
            #    # we can get a little performance out of selecting our LitCorr here
            #    # but also we need to do this because we are unconcerned with probes that have no geneId associated with them
            #    # as we would not have litCorr data.
            #
            #    if method == "3":
            #        query = "SELECT %s.Name, %s.value," %  (db.type,tempTable)
            #        dataStartPos = 2
            #    if method == "4" or method == "5":
            #        query = "SELECT %s.Name, %s.Correlation, %s.PValue," %  (db.type,tempTable, tempTable)
            #        dataStartPos = 3
            #
            #    query += string.join(temp,', ')
            #    query += ' FROM (%s, %sXRef, %sFreeze)' % (db.type, db.type, db.type)
            #    if method == "3":
            #        query += ' LEFT JOIN %s ON %s.GeneId2=ProbeSet.GeneId ' % (tempTable,tempTable)
            #    if method == "4" or method == "5":
            #        query += ' LEFT JOIN %s ON %s.Symbol=ProbeSet.Symbol ' % (tempTable,tempTable)
            #    #XZ, 03/04/2009: Xiaodong changed Data to %sData and changed parameters from %(item,item, db.type,item,item) to %(db.type, item,item, db.type,item,item)
            #    for item in StrainIdstep:
            #        query += 'left join %sData as T%s on T%s.Id = %sXRef.DataId and T%s.StrainId=%s\n' %(db.type, item,item, db.type,item,item)
            #
            #    if method == "3":
            #        query += "WHERE ProbeSet.GeneId IS NOT NULL AND %s.value IS NOT NULL AND %sXRef.%sFreezeId = %sFreeze.Id and %sFreeze.Name = '%s'  and %s.Id = %sXRef.%sId order by %s.Id" % (tempTable,db.type, db.type, db.type, db.type, db.name, db.type, db.type, db.type, db.type)
            #    if method == "4" or method == "5":
            #        query += "WHERE ProbeSet.Symbol IS NOT NULL AND %s.Correlation IS NOT NULL AND %sXRef.%sFreezeId = %sFreeze.Id and %sFreeze.Name = '%s'  and %s.Id = %sXRef.%sId order by %s.Id" % (tempTable,db.type, db.type, db.type, db.type, db.name, db.type, db.type, db.type, db.type)
            else:
                query = "SELECT %s.Name," %  db.type
                dataStartPos = 1
                query += string.join(temp,', ')
                query += ' FROM (%s, %sXRef, %sFreeze)' % (db.type, db.type, db.type)
                #XZ, 03/04/2009: Xiaodong changed Data to %sData and changed parameters from %(item,item, db.type,item,item) to %(db.type, item,item, db.type,item,item)
                for item in StrainIdstep:
                    query += 'left join %sData as T%s on T%s.Id = %sXRef.DataId and T%s.StrainId=%s\n' %(db.type, item,item, db.type,item,item)
                query += "WHERE %sXRef.%sFreezeId = %sFreeze.Id and %sFreeze.Name = '%s'  and %s.Id = %sXRef.%sId order by %s.Id" % (db.type, db.type, db.type, db.type, db.name, db.type, db.type, db.type, db.type)

            self.cursor.execute(query)
            results = self.cursor.fetchall()
            oridata.append(results)

        datasize = len(oridata[0])
        traits = []
        # put all of the separate data together into a huge list of lists
        for j in range(datasize):
            traitdata = list(oridata[0][j])
            for i in range(1,nnn):
                traitdata += list(oridata[i][j][dataStartPos:])

            trait = Trait(traitdata[0], traitdata[dataStartPos:])

            if method == METHOD_LIT:
                trait.lit_corr = traitdata[1]

            if method in TISSUE_METHODS:
                trait.tissue_corr = traitdata[1]
                trait.p_tissue = traitdata[2]

            traits.append(trait)

        if tempTable:
            self.cursor.execute( 'DROP TEMPORARY TABLE %s' % tempTable )

        return traits




    # XZ, 09/20/2008: This function creates TEMPORARY TABLE tmpTableName_2 and return its name.
    # XZ, 09/20/2008: It stores top literature correlation values associated with the input geneId.
    # XZ, 09/20/2008: Attention: In each row, the input geneId is always in column GeneId1.
    #XZ, 12/16/2008: the input geneid can be of mouse, rat or human type
    def getTempLiteratureTable(self, species, input_species_geneid, returnNumber):
        # according to mysql the TEMPORARY TABLE name should not have to be unique because
        # it is only available to the current connection. This program will be invoked via command line, but if it
        # were to be invoked over mod_python this could cuase problems.  mod_python will keep the connection alive
        # in its executing threads ( i think) so there is a potential for the table not being dropped between users.
        #XZ, 01/29/2009: To prevent the potential risk, I generate random table names and drop the tables after use them.


        # the 'input_species_geneid' could be rat or human geneid, need to translate it to mouse geneid
        translated_mouse_geneid = self.translateToMouseGeneID (species, input_species_geneid)

        tmpTableName_1 = webqtlUtil.genRandStr(prefix="LITERATURE")

        q1 = 'CREATE TEMPORARY TABLE %s (GeneId1 int(12) unsigned, GeneId2 int(12) unsigned PRIMARY KEY, value double)' % tmpTableName_1
        q2 = 'INSERT INTO %s (GeneId1, GeneId2, value) SELECT GeneId1,GeneId2,value FROM LCorrRamin3 WHERE GeneId1=%s' % (tmpTableName_1, translated_mouse_geneid)
        q3 = 'INSERT INTO %s (GeneId1, GeneId2, value) SELECT GeneId2,GeneId1,value FROM LCorrRamin3 WHERE GeneId2=%s AND GeneId1!=%s' % (tmpTableName_1, translated_mouse_geneid,translated_mouse_geneid)
        for x in [q1,q2,q3]: self.cursor.execute(x)

        #XZ, 09/23/2008: Just use the top records insteard of using all records
        tmpTableName_2 = webqtlUtil.genRandStr(prefix="TOPLITERATURE")

        q1 = 'CREATE TEMPORARY TABLE %s (GeneId1 int(12) unsigned, GeneId2 int(12) unsigned PRIMARY KEY, value double)' % tmpTableName_2
        self.cursor.execute(q1)
        q2 = 'SELECT GeneId1, GeneId2, value FROM %s ORDER BY value DESC' % tmpTableName_1
        self.cursor.execute(q2)
        result = self.cursor.fetchall()

        counter = 0 #this is to count how many records being inserted into table
        for one_row in result:
            mouse_geneid1, mouse_geneid2, lit_corr_alue = one_row

            #mouse_geneid1 has been tested before, now should test if mouse_geneid2 has corresponding geneid in other species
            translated_species_geneid = 0
            if species == 'mouse':
                translated_species_geneid = mouse_geneid2
            elif species == 'rat':
                self.cursor.execute( "SELECT rat FROM GeneIDXRef WHERE mouse=%d" % int(mouse_geneid2) )
                record = self.cursor.fetchone()
                if record:
                    translated_species_geneid = record[0]
            elif species == 'human':
                self.cursor.execute( "SELECT human FROM GeneIDXRef WHERE mouse=%d" % int(mouse_geneid2) )
                record = self.cursor.fetchone()
                if record:
                    translated_species_geneid = record[0]

            if translated_species_geneid:
                self.cursor.execute( 'INSERT INTO %s (GeneId1, GeneId2, value) VALUES (%d,%d,%f)' % (tmpTableName_2, int(input_species_geneid),int(translated_species_geneid), float(lit_corr_alue)) )
                counter = counter + 1

            #pay attention to the number
            if (counter > 2*returnNumber):
                break

        self.cursor.execute('DROP TEMPORARY TABLE %s' % tmpTableName_1)

        return tmpTableName_2



    #XZ, 01/09/2009: This function was created by David Crowell. Xiaodong cleaned up and modified it.
    def fetchLitCorrelations(self, species, GeneId, db, returnNumber): ### Used to generate Lit Correlations when calculations are done from text file.  dcrowell August 2008
        """Uses getTempLiteratureTable to generate table of literatire correlations.  This function then gathers that data and
        pairs it with the TraitID string.  Takes as its arguments a formdata instance, and a database instance.
        Returns a dictionary of 'TraitID':'LitCorr' for the requested correlation"""

        tempTable = self.getTempLiteratureTable(species=species, input_species_geneid=GeneId, returnNumber=returnNumber)

        query = "SELECT %s.Name, %s.value" %  (db.type,tempTable)
        query += ' FROM (%s, %sXRef, %sFreeze)' % (db.type, db.type, db.type)
        query += ' LEFT JOIN %s ON %s.GeneId2=ProbeSet.GeneId ' % (tempTable,tempTable)
        query += "WHERE ProbeSet.GeneId IS NOT NULL AND %s.value IS NOT NULL AND %sXRef.%sFreezeId = %sFreeze.Id and %sFreeze.Name = '%s'  and %s.Id = %sXRef.%sId order by %s.Id" % (tempTable, db.type, db.type, db.type, db.type, db.name, db.type, db.type, db.type, db.type)

        self.cursor.execute(query)
        results = self.cursor.fetchall()

        litCorrDict = {}

        for entry in results:
            traitName,litcorr = entry
            litCorrDict[traitName] = litcorr

        self.cursor.execute('DROP TEMPORARY TABLE %s' % tempTable)

        return litCorrDict


    def get_traits(self, vals):

        #Todo: Redo cached stuff using memcached
        if False:
            lit_corrs = {}
            tissue_corrs = {}
            use_lit = False
            if self.method == METHOD_LIT:
                lit_corrs = self.fetchLitCorrelations(species=self.species, GeneId=self.gene_id, db=self.db, returnNumber=self.returnNumber)
                use_lit = True

            use_tissue_corr = False
            if self.method in TISSUE_METHODS:
                tissue_corrs = self.fetch_tissue_correlations(method=self.method, return_number = self.return_number)
                use_tissue_corr = True

            DatabaseFileName = self.getFileName( target_db_name=self.target_db_name )
            datasetFile = open(webqtlConfig.CACHEDIR+DatabaseFileName,'r')

            #XZ, 01/08/2009: read the first line
            line = datasetFile.readline()
            cached_sample_names = webqtlUtil.readLineCSV(line)[1:]

            #XZ, 01/08/2009: This step is critical. It is necessary for this new method.
            #XZ: The original function fetchAllDatabaseData uses all strains stored in variable _strains to
            #XZ: retrieve the values of each strain from database in real time.
            #XZ: The new method uses all strains stored in variable dataset_strains to create a new variable
            #XZ: _newvals. _newvals has the same length as dataset_strains. The items in _newvals is in
            #XZ: the same order of items in dataset_strains. The value of each item in _newvals is either
            #XZ: the value of correspinding strain in _vals or 'None'.
            new_vals = []
            for name in cached_sample_names:
                if name in self.sample_names:
                    new_vals.append(float(vals[self.sample_names.index(name)]))
                else:
                    new_vals.append('None')

            nnCorr = len(new_vals)

            #XZ, 01/14/2009: If literature corr or tissue corr is selected,
            #XZ: there is no need to use parallel computing.

            traits = []
            data_start = 1
            for line in datasetFile:
                raw_trait = webqtlUtil.readLineCSV(line)
                trait = Trait.from_csv(raw_trait, data_start)
                trait.lit_corr = lit_corrs.get(trait.name)
                trait.tissue_corr, trait.p_tissue = tissue_corrs.get(trait.name, (None, None))
                traits.append(trait)

            return traits, new_vals

        else:
            traits = self.fetchAllDatabaseData(species=self.dataset.species,
                                               GeneId=self.gene_id,
                                               GeneSymbol=self.trait.symbol,
                                               strains=self.sample_names,
                                               db=self.db,
                                               method=self.method,
                                               returnNumber=self.returnNumber,
                                               tissueProbeSetFreezeId= self.tissue_probeset_freeze_id)
            totalTraits = len(traits) #XZ, 09/18/2008: total trait number

        return traits
			
    def calculate_corr_for_all_tissues(self, tissue_dataset_id=None):

        symbol_corr_dict = {}
        symbol_pvalue_dict = {}

        primary_trait_symbol_value_dict = correlation_functions.make_gene_tissue_value_dict(
                                                    GeneNameLst=[self.this_trait.symbol],
                                                    TissueProbeSetFreezeId=tissue_dataset_id)
        primary_trait_value = primary_trait_symbol_value_dict.values()[0]

        symbol_value_dict = correlation_functions.make_gene_tissue_value_dict(
                                        gene_name_list=[],
                                        tissue_dataset_id=tissue_dataset_id)

        symbol_corr_dict, symbol_pvalue_dict = correlation_functions.batch_cal_tissue_corr(
                primaryTraitValue,
                SymbolValueDict,
                method=self.corr_method)
        #else:
        #    symbol_corr_dict, symbol_pvalue_dict = correlation_functions.batch_cal_tissue_corr(
        #        primaryTraitValue,
        #        SymbolValueDict)

        return (symbolCorrDict, symbolPvalueDict)


    def correlate(self):
        self.correlation_data = collections.defaultdict(list)
        for trait, values in self.target_dataset.trait_data.iteritems():
            values_1 = []
            values_2 = []
            for index,sample in enumerate(self.target_dataset.samplelist):
                target_value = values[index]
                if sample in self.sample_data.keys():
                    this_value = self.sample_data[sample]
                    values_1.append(this_value)
                    values_2.append(target_value)
            correlation = calCorrelation(values_1, values_2)
            self.correlation_data[trait] = correlation
			
    def getFileName(self, target_db_name):  ### dcrowell  August 2008
        """Returns the name of the reference database file with which correlations are calculated.
        Takes argument cursor which is a cursor object of any instance of a subclass of templatePage
        Used by correlationPage"""

        dataset_id = str(self.target_dataset.id)
        dataset_fullname = self.target_dataset.fullname.replace(' ','_')
        dataset_fullname = dataset_fullname.replace('/','_')

        FileName = 'ProbeSetFreezeId_' + dataset_id + '_FullName_' + dataset_fullname + '.txt'

        return FileName

    def do_parallel_correlation(self, db_filename, num_overlap):
	
        #XZ, 01/14/2009: This method is for parallel computing only.
        #XZ: It is supposed to be called when "Genetic Correlation, Pearson's r" (method 1)
        #XZ: or "Genetic Correlation, Spearman's rho" (method 2) is selected
        def compute_corr(input_nnCorr, input_trait, input_list, corr_method):

            import math
            import reaper

            def calCorrelation(dbdata,userdata,N):
                X = []
                Y = []
                for i in range(N):
                    if (dbdata[i] != None and userdata[i] != None) and (dbdata[i] != "None" and userdata[i] != "None"):
                        X.append(float(dbdata[i]))
                        Y.append(float(userdata[i]))
                NN = len(X)
                if NN <6:
                    return (0.0,NN)
                sx = reduce(lambda x,y:x+y,X,0.0)
                sy = reduce(lambda x,y:x+y,Y,0.0)
                meanx = sx/NN
                meany = sy/NN
                xyd = 0.0
                sxd = 0.0
                syd = 0.0
                for i in range(NN):
                    xyd += (X[i] - meanx)*(Y[i]-meany)
                    sxd += (X[i] - meanx)*(X[i] - meanx)
                    syd += (Y[i] - meany)*(Y[i] - meany)
                try:
                    corr = xyd/(math.sqrt(sxd)*math.sqrt(syd))
                except:
                    corr = 0
                return (corr,NN)

            def calCorrelationRank(xVals,yVals,N):
                """
                Calculated Spearman Ranked Correlation. The algorithm works
                by setting all tied ranks to the average of those ranks (for
                example, if ranks 5-10 all have the same value, each will be set
                to rank 7.5).
                """

                XX = []
                YY = []
                j = 0

                for i in range(len(xVals)):
                    if (xVals[i]!= None and yVals[i]!= None) and (xVals[i] != "None" and yVals[i] != "None"):
                        XX.append((j,float(xVals[i])))
                        YY.append((j,float(yVals[i])))
                        j = j+1

                NN = len(XX)
                if NN <6:
                    return (0.0,NN)
                XX.sort(cmpOrder2)
                YY.sort(cmpOrder2)
                X = [0]*NN
                Y = [0]*NN

                j = 1
                rank = 0.0
                t = 0.0
                sx = 0.0

                while j < NN:

                    if XX[j][1] != XX[j-1][1]:
                        X[XX[j-1][0]] = j
                        j = j+1

                    else:
                        jt = j+1
                        ji = j
                        for jt in range(j+1, NN):
                            if (XX[jt][1] != XX[j-1][1]):
                                break
                        rank = 0.5*(j+jt)
                        for ji in range(j-1, jt):
                            X[XX[ji][0]] = rank
                        t = jt-j
                        sx = sx + (t*t*t-t)
                        if (jt == NN-1):
                            if (XX[jt][1] == XX[j-1][1]):
                                X[XX[NN-1][0]] = rank
                        j = jt+1

                if j == NN:
                    if X[XX[NN-1][0]] == 0:
                        X[XX[NN-1][0]] = NN

                j = 1
                rank = 0.0
                t = 0.0
                sy = 0.0

                while j < NN:

                    if YY[j][1] != YY[j-1][1]:
                        Y[YY[j-1][0]] = j
                        j = j+1
                    else:
                        jt = j+1
                        ji = j
                        for jt in range(j+1, NN):
                            if (YY[jt][1] != YY[j-1][1]):
                                break
                        rank = 0.5*(j+jt)
                        for ji in range(j-1, jt):
                            Y[YY[ji][0]] = rank
                        t = jt - j
                        sy = sy + (t*t*t-t)
                        if (jt == NN-1):
                            if (YY[jt][1] == YY[j-1][1]):
                                Y[YY[NN-1][0]] = rank
                        j = jt+1

                if j == NN:
                    if Y[YY[NN-1][0]] == 0:
                        Y[YY[NN-1][0]] = NN

                D = 0.0

                for i in range(NN):
                    D += (X[i]-Y[i])*(X[i]-Y[i])

                fac = (1.0 -sx/(NN*NN*NN-NN))*(1.0-sy/(NN*NN*NN-NN))

                return ((1-(6.0/(NN*NN*NN-NN))*(D+(sx+sy)/12.0))/math.sqrt(fac),NN)

            # allcorrelations = []

            correlation_data = {}
            for i, line in enumerate(input_list):
                if i == 0:
                    continue
                tokens = line.split('","')
                tokens[-1] = tokens[-1][:-2] #remove the last "
                tokens[0] = tokens[0][1:] #remove the first "

                traitdataName = tokens[0]
                database_trait = tokens[1:]

                #print("database_trait:", database_trait)

                #ZS: 2015 could add biweight correlation, see http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3465711/
                # if corr_method == 'pearson':
                    # sample_r, sample_p = scipy.stats.pearsonr(input_trait, database_trait)
                # else:
                    # sample_r, sample_p = scipy.stats.spearmanr(input_trait, database_trait)

                if corr_method == "pearson": #XZ: Pearson's r
                    sample_r, nOverlap = calCorrelation(input_trait, database_trait, input_nnCorr)
                else: #XZ: Spearman's rho
                    sample_r, nOverlap = calCorrelationRank(input_trait, database_trait, input_nnCorr)

                #XZ: calculate corrPValue
                if nOverlap < 3:
                    sample_p = 1.0
                else:
                    if abs(sample_r) >= 1.0:
                        sample_p = 0.0
                    else:
                        z_value = 0.5*math.log((1.0+sample_r)/(1.0-sample_r))
                        z_value = z_value*math.sqrt(nOverlap-3)
                        sample_p = 2.0*(1.0 - reaper.normp(abs(z_value)))

                correlation_data[traitdataName] = [sample_r, sample_p, nOverlap]	

                # traitinfo = [traitdataName, sample_r, nOverlap]
                # allcorrelations.append(traitinfo)

            return correlation_data
            # return allcorrelations

	
        datasetFile = open(webqtlConfig.GENERATED_TEXT_DIR+db_filename,'r')

        print("Invoking parallel computing")
        input_line_list = datasetFile.readlines()
        print("Read lines from the file")
        all_line_number = len(input_line_list)

        step = 1000
        job_number = math.ceil( float(all_line_number)/step )

        print("JOB NUMBER", job_number)

        job_input_lists = []

        print("Configuring jobs")

        for job_index in range( int(job_number) ):
            starti = job_index*step
            endi = min((job_index+1)*step, all_line_number)

            one_job_input_list = []

            for i in range( starti, endi ):
                one_job_input_list.append( input_line_list[i] )

            job_input_lists.append( one_job_input_list )

        print("Creating pp servers")

        ppservers = ()
        # Creates jobserver with automatically detected number of workers
        job_server = pp.Server(ppservers=ppservers)

        print("Done creating servers")

        jobs = []
        results = []

        print("Starting parallel computation, submitting jobs")
        for one_job_input_list in job_input_lists: #pay attention to modules from outside
            jobs.append( job_server.submit(func=compute_corr, args=(num_overlap, self.this_trait_vals, one_job_input_list, self.corr_method), depfuncs=(), modules=("webqtlUtil",)) )
        print("Done submitting jobs")

        for one_job in jobs:
            one_result = one_job()
            self.correlation_data.update(one_result)
            # one_result = one_job()
            # results.append( one_result )

        #print("CORRELATION DATA:", self.correlation_data)

        # print("Acquiring results")

        # for one_result in results:
            # for one_traitinfo in one_result:
                # allcorrelations.append( one_traitinfo )


