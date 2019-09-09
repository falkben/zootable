document.addEventListener("DOMContentLoaded", function() {
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
