// Generated by CoffeeScript 1.3.3
(function() {
  var Contains, fillOptions, fillOptionsForIE, getDefaultValue, getIndexByValue, initialDatasetSelection, removeOptions, setChoice, setDefault, updateChocie;

  initialDatasetSelection = function() {
    var dOptions, defaultDB, defaultSet, defaultSpecies, defaultType, gOptions, menu0, menu1, menu2, menu3, sOptions, tOptions;
    defaultSpecies = getDefaultValue("species");
    defaultSet = getDefaultValue("cross");
    defaultType = getDefaultValue("tissue");
    defaultDB = getDefaultValue("database");
    if (navigator.userAgent.indexOf("MSIE") >= 0) {
      sOptions = fillOptionsForIE(null, defaultSpecies);
      menu0 = "<SELECT NAME='species' ID='species' SIZE='1' onChange='fillOptions(\"species\");'>" + sOptions + "</Select>";
      document.getElementById("menu0").innerHTML = menu0;
      gOptions = fillOptionsForIE("species", defaultSet);
      menu1 = "<Select NAME='cross' size=1 id='cross' onchange='fillOptions(\"cross\");'>" + gOptions + "</Select><input type=\"button\" class=\"button\" value=\"Info\" onCLick=\"javascript:crossinfo();\">";
      document.getElementById("menu1").innerHTML = menu1;
      tOptions = fillOptionsForIE("cross", defaultType);
      menu2 = "<Select NAME='tissue' size=1 id='tissue' onchange='fillOptions(\"tissue\");'>" + tOptions + "</Select>";
      document.getElementById("menu2").innerHTML = menu2;
      dOptions = fillOptionsForIE("tissue", defaultDB);
      menu3 = "<Select NAME='database' size=1 id='database'>" + dOptions + "</Select><input type=\"button\" class=\"button\" value=\"Info\" onCLick=\"javascript:databaseinfo();\">";
      document.getElementById("menu3").innerHTML = menu3;
    } else {
      fillOptions(null);
    }
    return searchtip();
  };

  fillOptionsForIE = function(selectObjId, defaultValue) {
    var arr, groupObj, i, idx, len, options, speciesObj, typeObj;
    options = "";
    if (selectObjId == null) {
      len = sArr.length;
      i = 1;
      while (i < len) {
        if (sArr[i].val === defaultValue) {
          options = options + "<option selected=\"selected\" value='" + sArr[i].val + "'>" + sArr[i].txt + "</option>";
        } else {
          options = options + "<option value='" + sArr[i].val + "'>" + sArr[i].txt + "</option>";
        }
        i++;
      }
    } else if (selectObjId === "species") {
      speciesObj = document.getElementById("species");
      len = lArr.length;
      arr = [];
      idx = 0;
      i = 1;
      while (i < len) {
        if (lArr[i][0] === (getIndexByValue("species", speciesObj.value)).toString() && !Contains(arr, lArr[i][1])) {
          arr[idx++] = lArr[i][1];
        }
        i++;
      }
      idx = 0;
      len = arr.length;
      removeOptions("cross");
      i = 0;
      while (i < len) {
        if (gArr[arr[i]].val === defaultValue) {
          options = options + "<option selected=\"selected\" value='" + gArr[arr[i]].val + "'>" + gArr[arr[i]].txt + "</option>";
        } else {
          options = options + "<option value='" + gArr[arr[i]].val + "'>" + gArr[arr[i]].txt + "</option>";
        }
        i++;
      }
    } else if (selectObjId === "cross") {
      speciesObj = document.getElementById("species");
      groupObj = document.getElementById("cross");
      len = lArr.length;
      arr = [];
      idx = 0;
      i = 1;
      while (i < len) {
        if (lArr[i][0] === (getIndexByValue("species", speciesObj.value)).toString() && lArr[i][1] === (getIndexByValue("cross", groupObj.value)).toString() && !Contains(arr, lArr[i][2])) {
          arr[idx++] = lArr[i][2];
        }
        i++;
      }
      idx = 0;
      len = arr.length;
      removeOptions("tissue");
      i = 0;
      while (i < len) {
        if (tArr[arr[i]].val === defaultValue) {
          options = options + "<option selected=\"selected\" value='" + tArr[arr[i]].val + "'>" + tArr[arr[i]].txt + "</option>";
        } else {
          options = options + "<option value='" + tArr[arr[i]].val + "'>" + tArr[arr[i]].txt + "</option>";
        }
        i++;
      }
    } else if (selectObjId === "tissue") {
      speciesObj = document.getElementById("species");
      groupObj = document.getElementById("cross");
      typeObj = document.getElementById("tissue");
      len = lArr.length;
      arr = [];
      idx = 0;
      i = 1;
      while (i < len) {
        if (lArr[i][0] === (getIndexByValue("species", speciesObj.value)).toString() && lArr[i][1] === (getIndexByValue("cross", groupObj.value)).toString() && lArr[i][2] === (getIndexByValue("tissue", typeObj.value)).toString() && !Contains(arr, lArr[i][3])) {
          arr[idx++] = lArr[i][3];
        }
        i++;
      }
      idx = 0;
      len = arr.length;
      removeOptions("database");
      i = 0;
      while (i < len) {
        if (dArr[arr[i]].val === defaultValue) {
          options = options + "<option SELECTED value='" + dArr[arr[i]].val + "'>" + dArr[arr[i]].txt + "</option>";
        } else {
          options = options + "<option value='" + dArr[arr[i]].val + "'>" + dArr[arr[i]].txt + "</option>";
        }
        i++;
      }
    }
    return options;
  };

  fillOptions = function(selectObjId) {
    var arr, databaseObj, groupObj, i, idx, len, speciesObj, typeObj;
    if (selectObjId == null) {
      speciesObj = document.getElementById("species");
      len = sArr.length;
      i = 1;
      while (i < len) {
        speciesObj.options[i - 1] = new Option(sArr[i].txt, sArr[i].val);
        i++;
      }
      return updateChocie("species");
    } else if (selectObjId === "species") {
      speciesObj = document.getElementById("species");
      groupObj = document.getElementById("cross");
      len = lArr.length;
      arr = [];
      idx = 0;
      i = 1;
      while (i < len) {
        if (lArr[i][0] === (getIndexByValue("species", speciesObj.value)).toString() && !Contains(arr, lArr[i][1])) {
          arr[idx++] = lArr[i][1];
        }
        i++;
      }
      idx = 0;
      len = arr.length;
      removeOptions("cross");
      i = 0;
      while (i < len) {
        groupObj.options[idx++] = new Option(gArr[arr[i]].txt, gArr[arr[i]].val);
        i++;
      }
      return updateChocie("cross");
    } else if (selectObjId === "cross") {
      speciesObj = document.getElementById("species");
      groupObj = document.getElementById("cross");
      typeObj = document.getElementById("tissue");
      len = lArr.length;
      arr = [];
      idx = 0;
      i = 1;
      while (i < len) {
        if (lArr[i][0] === (getIndexByValue("species", speciesObj.value)).toString() && lArr[i][1] === (getIndexByValue("cross", groupObj.value)).toString() && !Contains(arr, lArr[i][2])) {
          arr[idx++] = lArr[i][2];
        }
        i++;
      }
      idx = 0;
      len = arr.length;
      removeOptions("tissue");
      i = 0;
      while (i < len) {
        typeObj.options[idx++] = new Option(tArr[arr[i]].txt, tArr[arr[i]].val);
        i++;
      }
      return updateChocie("tissue");
    } else if (selectObjId === "tissue") {
      speciesObj = document.getElementById("species");
      groupObj = document.getElementById("cross");
      typeObj = document.getElementById("tissue");
      databaseObj = document.getElementById("database");
      len = lArr.length;
      arr = [];
      idx = 0;
      i = 1;
      while (i < len) {
        if (lArr[i][0] === (getIndexByValue("species", speciesObj.value)).toString() && lArr[i][1] === (getIndexByValue("cross", groupObj.value)).toString() && lArr[i][2] === (getIndexByValue("tissue", typeObj.value)).toString() && !Contains(arr, lArr[i][3])) {
          arr[idx++] = lArr[i][3];
        }
        i++;
      }
      idx = 0;
      len = arr.length;
      removeOptions("database");
      i = 0;
      while (i < len) {
        databaseObj.options[idx++] = new Option(dArr[arr[i]].txt, dArr[arr[i]].val);
        i++;
      }
      return updateChocie("database");
    }
  };

  Contains = function(arr, obj) {
    var i;
    i = arr.length;
    if ((function() {
      var _results;
      _results = [];
      while (i--) {
        _results.push(arr[i] === obj);
      }
      return _results;
    })()) {
      return true;
    }
    return false;
  };

  removeOptions = function(selectObj) {
    var i, len, _results;
    if (typeof selectObj !== "object") {
      selectObj = document.getElementById(selectObj);
    }
    len = selectObj.options.length;
    i = 0;
    _results = [];
    while (i < len) {
      selectObj.options[0] = null;
      _results.push(i++);
    }
    return _results;
  };

  getIndexByValue = function(selectObjId, val) {
    var i;
    if (selectObjId === "species") {
      i = 1;
      while (i < sArr.length) {
        if (sArr[i].val === val) {
          return i;
        }
        i++;
      }
    } else if (selectObjId === "cross") {
      i = 1;
      while (i < gArr.length) {
        if (gArr[i].val === val) {
          return i;
        }
        i++;
      }
    } else if (selectObjId === "tissue") {
      i = 1;
      while (i < tArr.length) {
        if (tArr[i].val === val) {
          return i;
        }
        i++;
      }
    } else {

    }
  };

  setChoice = function(objId, val) {
    var Obj, i, idx;
    Obj = document.getElementById(objId);
    idx = -1;
    i = 0;
    while (i < Obj.options.length) {
      if (Obj.options[i].value === val) {
        idx = i;
        break;
      }
      i++;
    }
    if (idx >= 0) {
      Obj.options[idx].selected = true;
      return fillOptions(objId);
    } else {
      Obj.options[0].selected = true;
      return fillOptions(objId);
    }
  };

  updateChocie = function(selectObjId) {
    var defaultDB, defaultSet, defaultSpecies, defaultType;
    if (selectObjId === "species") {
      defaultSpecies = getDefaultValue("species");
      return setChoice("species", defaultSpecies);
    } else if (selectObjId === "cross") {
      defaultSet = getDefaultValue("cross");
      return setChoice("cross", defaultSet);
    } else if (selectObjId === "tissue") {
      defaultType = getDefaultValue("tissue");
      return setChoice("tissue", defaultType);
    } else if (selectObjId === "database") {
      defaultDB = getDefaultValue("database");
      return setChoice("database", defaultDB);
    }
  };

  getDefaultValue = function(selectObjId) {
    var cookieDB, cookieSet, cookieSpecies, cookieType, defaultDB, defaultSet, defaultSpecies, defaultType;
    defaultSpecies = "mouse";
    defaultSet = "BXD";
    defaultType = "Hippocampus";
    defaultDB = "HC_M2_0606_P";
    if (selectObjId === "species") {
      cookieSpecies = getCookie("defaultSpecies");
      if (cookieSpecies) {
        defaultSpecies = cookieSpecies;
      }
      return defaultSpecies;
    } else if (selectObjId === "cross") {
      cookieSet = getCookie("defaultSet");
      if (cookieSet) {
        defaultSet = cookieSet;
      }
      return defaultSet;
    } else if (selectObjId === "tissue") {
      cookieType = getCookie("defaultType");
      if (cookieType) {
        defaultType = cookieType;
      }
      return defaultType;
    } else if (selectObjId === "database") {
      cookieDB = getCookie("defaultDB");
      if (cookieDB) {
        defaultDB = cookieDB;
      }
      return defaultDB;
    }
  };

  setDefault = function(thisform) {
    var cookieTest, defaultDB, defaultSet, defaultSpecies, defaultType;
    setCookie("cookieTest", "cookieTest", 1);
    cookieTest = getCookie("cookieTest");
    delCookie("cookieTest");
    if (cookieTest) {
      defaultSpecies = thisform.species.value;
      setCookie("defaultSpecies", defaultSpecies, 10);
      defaultSet = thisform.cross.value;
      setCookie("defaultSet", defaultSet, 10);
      defaultType = thisform.tissue.value;
      setCookie("defaultType", defaultType, 10);
      defaultDB = thisform.database.value;
      setCookie("defaultDB", defaultDB, 10);
      updateChocie("species");
      updateChocie("cross");
      updateChocie("tissue");
      updateChocie("database");
      return alert("The current settings are now your default");
    } else {
      return alert("You need to enable Cookies in your browser.");
    }
  };

}).call(this);
