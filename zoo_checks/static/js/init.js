// initialization
document.addEventListener("DOMContentLoaded", function () {
  var elems = document.querySelectorAll("select");
  var instances = M.FormSelect.init(elems, {});
});

document.addEventListener("DOMContentLoaded", function () {
  var elems = document.querySelectorAll(".sidenav");
  var instances = M.Sidenav.init(elems, {});
});

document.addEventListener("DOMContentLoaded", function () {
  var elems = document.querySelectorAll(".datepicker");
  var today = new Date();
  var instances = M.Datepicker.init(elems, {
    format: "mm/dd/yyyy",
    maxDate: today,
    autoClose: true,
  });
});

document.addEventListener("DOMContentLoaded", function () {
  var elems = document.querySelectorAll(".tooltipped");
  var instances = M.Tooltip.init(elems, {});
});

function change_tally_form() {
  const tally_date = document.getElementById("id_tally_date").value;
  if (tally_date != "") {
    document.getElementById("datepicker_form").submit();
  }
}

// this overwrites the init for all datepicker's above
document.addEventListener("DOMContentLoaded", function () {
  var elems = document.querySelectorAll("#id_tally_date");
  var today = new Date();
  var instances = M.Datepicker.init(elems, {
    format: "mm/dd/yyyy",
    maxDate: today,
    autoClose: false,
    onClose: function () {
      change_tally_form();
    },
  });
});

function incrementValue(id, inc_val) {
  var value = parseInt(document.getElementById(id).value, 10);
  value = isNaN(value) ? 0 : value;
  if (value + inc_val >= 0) {
    value += inc_val;
    document.getElementById(id).value = value;
  }
}

function chartVisible(id) {
  document.getElementById(id).style.display = "block";
  document.getElementById(id + "-btn").classList.add("disabled");

  const elems = ["line-chart-opt", "pie-chart-opt"];
  let index = elems.indexOf(id);
  if (index > -1) {
    elems.splice(index, 1);
  }

  elems.forEach((item, index) => {
    document.getElementById(item).style.display = "none";
    document.getElementById(item + "-btn").classList.remove("disabled");
  });
}

document
  .querySelectorAll(".condition-radio input[type=radio]")
  .forEach((elem) => {
    elem.addEventListener("click", function (e) {
      // needs attention causes comment field to appear
      let comment_field =
        elem.parentElement.parentElement.parentElement.nextElementSibling;
      if (elem.value === "NA" || elem.value === "NS") {
        comment_field.style.display = "block";
      }
    });
  });

function update_count_bar(slider_elem) {
  const count_bar_id = slider_elem.id.replace("_slider", "");
  document.getElementById(count_bar_id).value = slider_elem.value;
}

function update_count_seen(slider_elem) {
  // const total = slider_elem.max;
  const count_seen_id = slider_elem.id.replace("_slider", "");
  document.getElementById(count_seen_id).value = slider_elem.value;

  update_bar_elems(
    slider_elem.id.replace("_seen_slider", "_bar_slider"),
    slider_elem.value
  );
}

function update_bar_elems(count_bar_id, seen_value) {
  //set the slider max value for BAR
  const count_bar = document.getElementById(count_bar_id);
  if (parseInt(seen_value) < parseInt(count_bar.value)) {
    // set the count_bar value to max of seen and BAR
    count_bar.value = seen_value;
    update_count_bar(count_bar);
  }
  count_bar.max = seen_value;
}

function update_slider(slider_id, value) {
  document.getElementById(slider_id).value = value;
}

document.querySelectorAll(".count_seen_slider").forEach((elem) => {
  elem.addEventListener("input", function (e) {
    update_count_seen(elem);
  });
});

document.querySelectorAll(".count_bar_slider").forEach((elem) => {
  elem.addEventListener("input", function (e) {
    update_count_bar(elem);
  });
});

document
  .querySelectorAll(".count_seen_input,.count_bar_input")
  .forEach((elem) => {
    elem.addEventListener("input", function (e) {
      update_slider(elem.id + "_slider", elem.value);
      if (elem.className.includes("count_seen_input")) {
        update_bar_elems(
          elem.id.replace("_seen", "_bar") + "_slider",
          elem.value
        );
      }
    });
  });

function count_species_animals_conditions(condition_radio_td_id) {
  // get the number of individuals in a species
  const input_selector = "td#" + condition_radio_td_id;

  // total number of animals
  const elem_total = document.querySelectorAll(input_selector).length;

  const radio_selector =
    input_selector + " .condition-radio input[type=radio]:checked";

  // number not_seen
  const not_seen = document.querySelectorAll(radio_selector + '[value="NS"]')
    .length;

  // number counted (anything not "not seen" or unmarked)
  const cond_counted = document.querySelectorAll(
    radio_selector + ':not([value="NS"]):not([value=""])'
  ).length;

  return [cond_counted, not_seen, elem_total];
}

function update_species_count_w_condition(elem) {
  // elem (input radio) > label > span > div > td
  // td.id gets us the species selector
  const condition_radio_td_id =
    elem.parentElement.parentElement.parentElement.parentElement.id;

  // we count the radio buttons
  const [cond_counted, not_seen, elem_total] = count_species_animals_conditions(
    condition_radio_td_id
  );

  // we go up to the form in order to get the species count input text box
  const species_form_id = condition_radio_td_id.replace(
    "_animal_condition_form",
    "_form"
  );
  const q_sel = "td#" + species_form_id + " p input";
  const species_input = document.querySelector(q_sel);

  const current_tally = parseInt(species_input.value);
  if (current_tally > elem_total - not_seen) {
    species_input.value = elem_total - not_seen;
  } else if (current_tally < cond_counted) {
    species_input.value = cond_counted;
  }
}

document
  .querySelectorAll(".tally-table-body .condition-radio input[type=radio]")
  .forEach((elem) => {
    elem.addEventListener("click", function (e) {
      update_species_count_w_condition(elem);
    });
  });

document.querySelectorAll(".msg").forEach((elem) => {
  elem.addEventListener("animationend", () => {
    elem.style.display = "none";
  });
});

function fill_conditions(selectObject) {
  const species_id = selectObject.id.replace("condition-fill-", "");
  const cond_val = selectObject.value;

  // protect against unlikely scenario that they somehow selected the fill descriptor option
  if (cond_val !== "fill") {
    const selector_string =
      "td#species_" +
      species_id +
      "_animal_condition_form div.fieldWrapper.condition-radio input[type=radio]" +
      "[value='" +
      cond_val +
      "']";

    let radio_elems = document.querySelectorAll(selector_string);
    // wanted for loop instead of forEach because we update species count on only last radio button changed
    for (var i = 0; i < radio_elems.length; i++) {
      radio_elems[i].checked = 1;
      if (i == radio_elems.length - 1) {
        update_species_count_w_condition(radio_elems[i]);
      }
    }

    selectObject.value = "fill";
  }
}

function display_detail_table(selector_string) {
  // used to show/hide the detail table on enclosure listing
  const table_elems = document.querySelectorAll(selector_string);
  table_elems.forEach((table_elem) => {
    if (table_elem.style.display === "none") {
      table_elem.style.display = "block";
    } else {
      table_elem.style.display = "none";
    }
  });
}
