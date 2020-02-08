document.addEventListener("DOMContentLoaded", function () {
  var elems = document.querySelectorAll(".sidenav");
  var instances = M.Sidenav.init(elems, {});
});

document.querySelectorAll("input[type=radio]").forEach(elem => {
  elem.addEventListener("click", allowUncheck);
  // only needed if elem can be pre-checked
  elem.previous = elem.checked;
});

function allowUncheck(e) {
  if (this.previous) {
    this.checked = false;
  }
  // need to update previous on all elements of this group
  // (either that or store the id of the checked element)
  document
    .querySelectorAll(`input[type=radio][name=${this.name}]`)
    .forEach(elem => {
      elem.previous = elem.checked;
    });
}

document.addEventListener("DOMContentLoaded", function () {
  var elems = document.querySelectorAll(".datepicker");
  var today = new Date();
  var instances = M.Datepicker.init(elems, {
    format: "mm/dd/yyyy",
    maxDate: today,
    onClose: function () {
      tally_date = document.getElementById("id_tally_date").value;
      if (tally_date != "") {
        form = document.getElementById("datepicker_form");
        console.log(tally_date)
        form.submit()
      }
    }
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
  .forEach(elem => {
    elem.addEventListener("click", function (e) {
      // needs attention causes comment field to appear
      let comment_field =
        elem.parentElement.parentElement.parentElement.nextElementSibling;
      if (elem.value === "NA" || elem.value === "NS") {
        comment_field.style.display = "block";
      }
    });
  });
