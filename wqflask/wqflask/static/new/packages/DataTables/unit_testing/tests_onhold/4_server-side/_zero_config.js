// DATA_TEMPLATE: empty_table
/*
 * NOTE: There are some differences in this zero config script for server-side
 * processing compared to the other data sources. The main reason for this is the
 * difference in how the server-side processing does it's filtering. Also the
 * sorting state is always reset on each draw.
 */
oTest.fnStart( "Sanity checks for DataTables with data from JS" );

oTest.fnWaitTest(
	"jQuery.dataTable function",
	null,
	function () { return typeof jQuery().dataTable == "function"; }
);

oTest.fnWaitTest(
	"jQuery.dataTableSettings storage array",
	null,
	function () { return typeof jQuery().dataTableSettings == "object"; }
);

oTest.fnWaitTest(
	"jQuery.dataTableExt plugin object",
	null,
	function () { return typeof jQuery().dataTableExt == "object"; }
);

$(document).ready( function () {
	$('#example').dataTable( {
		"bServerSide": true,
		"sAjaxSource": "../../../examples/server_side/scripts/server_processing.php"
	} );
	
	/* Basic checks */
	oTest.fnWaitTest(
		"Length changing div exists",
		null,
		function () { return document.getElementById('example_length') != null; }
	);
	
	oTest.fnWaitTest(
		"Filtering div exists",
		null,
		function () { return document.getElementById('example_filter') != null; }
	);
	
	oTest.fnWaitTest(
		"Information div exists",
		null,
		function () { return document.getElementById('example_info') != null; }
	);
	
	oTest.fnWaitTest(
		"Pagination div exists",
		null,
		function () { return document.getElementById('example_paginate') != null; }
	);
	
	oTest.fnWaitTest(
		"Processing div is off by default",
		null,
		function () { return document.getElementById('example_processing') == null; }
	);
	
	oTest.fnWaitTest(
		"10 rows shown on the first page",
		null,
		function () { return $('#example tbody tr').length == 10; }
	);
	
	oTest.fnWaitTest(
		"Initial sort occured",
		null,
		function () { return $('#example tbody td:eq(0)').html() == "Gecko"; }
	);
	
	/* Need to use the WaitTest for sorting due to the setTimeout datatables uses */
	oTest.fnWaitTest(
		"Sorting (first click) on second column",
		function () { $('#example thead th:eq(1)').click(); },
		function () { return $('#example tbody td:eq(1)').html() == "All others"; }
	);
	
	oTest.fnWaitTest(
		"Sorting (second click) on second column",
		function () { $('#example thead th:eq(1)').click(); },
		function () { return $('#example tbody td:eq(1)').html() == "Seamonkey 1.1"; }
	);
	
	oTest.fnWaitTest(
		"Sorting (third click) on second column",
		function () { $('#example thead th:eq(1)').click(); },
		function () { return $('#example tbody td:eq(1)').html() == "All others"; }
	);
	
	oTest.fnWaitTest(
		"Sorting (first click) on numeric column",
		function () { $('#example thead th:eq(3)').click(); },
		function () { return $('#example tbody td:eq(3)').html() == "-"; }
	);
	
	oTest.fnWaitTest(
		"Sorting (second click) on numeric column",
		function () { $('#example thead th:eq(3)').click(); },
		function () { return $('#example tbody td:eq(3)').html() == "522.1"; }
	);
	
	oTest.fnWaitTest(
		"Sorting multi-column (first click)",
		function () {
			$('#example thead th:eq(0)').click();
			oDispacher.click( $('#example thead th:eq(1)')[0], { 'shift': true } ); },
		function () { var b =
			$('#example tbody td:eq(0)').html() == "Gecko" &&
			$('#example tbody td:eq(1)').html() == "Camino 1.0"; return b; }
	);
	
	oTest.fnWaitTest(
		"Sorting multi-column - sorting first column only",
		function () {
			$('#example thead th:eq(0)').click(); },
		function () { var b =
			$('#example tbody td:eq(0)').html() == "Gecko" &&
			$('#example tbody td:eq(1)').html() == "Firefox 1.0"; return b; }
	);
	
	/* Basic paging */
	oTest.fnWaitTest(
		"Paging to second page",
		function () { $('#example_next').click(); },
		function () { return $('#example tbody td:eq(1)').html() == "Mozilla 1.1"; }
	);
	
	oTest.fnWaitTest(
		"Paging to first page",
		function () { $('#example_previous').click(); },
		function () { return $('#example tbody td:eq(1)').html() == "Firefox 1.0"; }
	);
	
	oTest.fnWaitTest(
		"Attempting to page back beyond the first page",
		function () { $('#example_previous').click(); },
		function () { return $('#example tbody td:eq(1)').html() == "Firefox 1.0"; }
	);
	
	/* Changing length */
	oTest.fnWaitTest(
		"Changing table length to 25 records",
		function () { $("select[name=example_length]").val('25').change(); },
		function () { return $('#example tbody tr').length == 25; }
	);
	
	oTest.fnWaitTest(
		"Changing table length to 50 records",
		function () { $("select[name=example_length]").val('50').change(); },
		function () { return $('#example tbody tr').length == 50; }
	);
	
	oTest.fnWaitTest(
		"Changing table length to 100 records",
		function () { $("select[name=example_length]").val('100').change(); },
		function () { return $('#example tbody tr').length == 57; }
	);
	
	oTest.fnWaitTest(
		"Changing table length to 10 records",
		function () { $("select[name=example_length]").val('10').change(); },
		function () { return $('#example tbody tr').length == 10; }
	);
	
	/*
	 * Information element
	 */
	oTest.fnWaitTest(
		"Information on zero config",
		null,
		function () { return document.getElementById('example_info').innerHTML == "Showing 1 to 10 of 57 entries"; }
	);
	
	oTest.fnWaitTest(
		"Information on second page",
		function () { $('#example_next').click(); },
		function () { return document.getElementById('example_info').innerHTML == "Showing 11 to 20 of 57 entries"; }
	);
	
	oTest.fnWaitTest(
		"Information on third page",
		function () { $('#example_next').click(); },
		function () { return document.getElementById('example_info').innerHTML == "Showing 21 to 30 of 57 entries"; }
	);
	
	oTest.fnWaitTest(
		"Information on last page",
		function () {
			$('#example_next').click();
			$('#example_next').click();
			$('#example_next').click();
		},
		function () { return document.getElementById('example_info').innerHTML == "Showing 51 to 57 of 57 entries"; }
	);
	
	oTest.fnWaitTest(
		"Information back on first page",
		function () {
			$('#example_previous').click();
			$('#example_previous').click();
			$('#example_previous').click();
			$('#example_previous').click();
			$('#example_previous').click();
		},
		function () { return document.getElementById('example_info').innerHTML == "Showing 1 to 10 of 57 entries"; }
	);
	
	oTest.fnWaitTest(
		"Information with 25 records",
		function () { $("select[name=example_length]").val('25').change(); },
		function () { return document.getElementById('example_info').innerHTML == "Showing 1 to 25 of 57 entries"; }
	);
	
	oTest.fnWaitTest(
		"Information with 25 records - second page",
		function () { $('#example_next').click(); },
		function () { return document.getElementById('example_info').innerHTML == "Showing 26 to 50 of 57 entries"; }
	);
	
	oTest.fnWaitTest(
		"Information with 100 records - first page",
		function () {
			$('#example_previous').click();
			$("select[name=example_length]").val('100').change();
		},
		function () { return document.getElementById('example_info').innerHTML == "Showing 1 to 57 of 57 entries"; }
	);
	
	oTest.fnWaitTest(
		"Information back to 10 records",
		function () {
			$('#example_previous').click();
			$("select[name=example_length]").val('10').change();
		},
		function () { return document.getElementById('example_info').innerHTML == "Showing 1 to 10 of 57 entries"; }
	);
	
	oTest.fnWaitTest(
		"Information with filter 'Win'",
		function () { $('#example_filter input').val("Win").keyup(); },
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 1 to 10 of 31 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Information with filter 'Win' second page",
		function () { $('#example_next').click(); },
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 11 to 20 of 31 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Information with filter 'Win' last page",
		function () {
			$('#example_next').click();
			$('#example_next').click();
		},
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 31 to 31 of 31 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Information with filter 'Win' back to first page",
		function () {
			$('#example_previous').click();
			$('#example_previous').click();
			$('#example_previous').click();
		},
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 1 to 10 of 31 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Information with filter 'Win' second page - second time",
		function () {
			$('#example_next').click();
		},
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 11 to 20 of 31 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Information with filter increased to 'Win 98'",
		function () { $('#example_filter input').val("Win 98").keyup(); },
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 1 to 9 of 9 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Information with filter decreased to 'Win'",
		function () { $('#example_filter input').val("Win").keyup(); },
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 1 to 10 of 31 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Information with filter 'Win' second page - third time",
		function () {
			$('#example_next').click();
		},
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 11 to 20 of 31 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Information with filter removed",
		function () { $('#example_filter input').val("").keyup(); },
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 1 to 10 of 57 entries"; }
	);
	
	
	/*
	 * Filtering
	 */
	oTest.fnWaitTest(
		"Filter 'W' - rows",
		function () {
			$('#example_filter input').val("W").keyup(); },
		function () { return $('#example tbody tr:eq(4) td:eq(1)').html() == "Netscape 7.2"; }
	);
	
	oTest.fnWaitTest(
		"Filter 'W' - info",
		null,
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 1 to 10 of 42 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Filter 'Wi'",
		function () { $('#example_filter input').val("Wi").keyup(); },
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 1 to 10 of 32 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Filter 'Win'",
		function () { $('#example_filter input').val("Win").keyup(); },
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 1 to 10 of 31 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Filter 'Win' - sorting column 1",
		function () { $('#example thead th:eq(1)').click(); },
		function () { return $('#example tbody tr:eq(0) td:eq(1)').html() == "AOL browser (AOL desktop)"; }
	);
	
	oTest.fnWaitTest(
		"Filter 'Win' - sorting column 1 info",
		null,
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 1 to 10 of 31 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Filter 'Win' - sorting column 1 reverse",
		function () { $('#example thead th:eq(1)').click(); },
		function () { return $('#example tbody tr:eq(0) td:eq(1)').html() == "Seamonkey 1.1"; }
	);
	
	oTest.fnWaitTest(
		"Filter 'Win XP' - maintaing reverse sorting col 1",
		function () { $('#example_filter input').val("Win XP").keyup(); },
		function () { return $('#example tbody tr:eq(0) td:eq(1)').html() == "Internet Explorer 7"; }
	);
	
	oTest.fnWaitTest(
		"Filter 'Win XP' - sorting col 3",
		function () { $('#example thead th:eq(3)').click(); },
		function () { return $('#example tbody tr:eq(0) td:eq(3)').html() == "6"; }
	);
	
	/* Note the filtering is different from the DOM since the server doesn't do
	 * "smart filtering" like the client side does
	 */
	oTest.fnWaitTest(
		"Filter 'Win XP' - sorting col 3 - reversed",
		function () { $('#example thead th:eq(3)').click(); },
		function () { return $('#example tbody tr:eq(0) td:eq(3)').html() == "7"; }
	);
	
	oTest.fnWaitTest(
		"Filter 'Win' - sorting col 3 - reversed info",
		null,
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 1 to 2 of 2 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Filter 'nothinghere'",
		function () { $('#example_filter input').val("nothinghere").keyup(); },
		function () { return $('#example tbody tr:eq(0) td:eq(0)').html() ==
			"No matching records found"; }
	);
	
	oTest.fnWaitTest(
		"Filter 'nothinghere' - info",
		null,
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 0 to 0 of 0 entries (filtered from 57 total entries)"; }
	);
	
	oTest.fnWaitTest(
		"Filter back to blank and 1st column sorting",
		function () {
			$('#example_filter input').val("").keyup();
			$('#example thead th:eq(0)').click();
		},
		function () { return document.getElementById('example_info').innerHTML ==
			"Showing 1 to 10 of 57 entries"; }
	);
	
	
	
	oTest.fnComplete();
} );