(function () {
  "use strict";

  function setupDocTabs() {
    var tabButtons = document.querySelectorAll(".tabs__btn");
    var panels = document.querySelectorAll(".tab-panel");
    if (!tabButtons.length) return;

    tabButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var target = btn.getAttribute("data-tab-target");

        tabButtons.forEach(function (b) {
          b.setAttribute("aria-selected", String(b === btn));
        });

        panels.forEach(function (panel) {
          var isTarget = panel.getAttribute("data-tab-panel") === target;
          panel.hidden = !isTarget;
          if (!isTarget) {
            // Vide les champs des onglets masques pour que seul l'onglet visible soit soumis.
            panel.querySelectorAll("input, textarea").forEach(function (field) {
              if (field.type === "file") {
                field.value = "";
                var dz = field.closest(".dropzone");
                if (dz) {
                  dz.classList.remove("has-file");
                  var label = dz.querySelector(".dropzone__filename");
                  if (label) label.textContent = "";
                }
              } else {
                field.value = "";
              }
            });
          }
        });
      });
    });
  }

  function setupDropzone() {
    var dropzone = document.querySelector(".dropzone");
    if (!dropzone) return;
    var input = dropzone.querySelector('input[type="file"]');
    var filenameLabel = dropzone.querySelector(".dropzone__filename");

    function showFile(file) {
      if (!file) {
        dropzone.classList.remove("has-file");
        filenameLabel.textContent = "";
        return;
      }
      dropzone.classList.add("has-file");
      var sizeKo = Math.round(file.size / 1024);
      filenameLabel.textContent = file.name + " (" + sizeKo + " Ko)";
    }

    dropzone.addEventListener("click", function () {
      input.click();
    });
    dropzone.addEventListener("keydown", function (evt) {
      if (evt.key === "Enter" || evt.key === " ") {
        evt.preventDefault();
        input.click();
      }
    });
    input.addEventListener("change", function () {
      showFile(input.files && input.files[0]);
    });

    ["dragenter", "dragover"].forEach(function (evtName) {
      dropzone.addEventListener(evtName, function (evt) {
        evt.preventDefault();
        dropzone.classList.add("is-dragover");
      });
    });
    ["dragleave", "dragend"].forEach(function (evtName) {
      dropzone.addEventListener(evtName, function () {
        dropzone.classList.remove("is-dragover");
      });
    });
    dropzone.addEventListener("drop", function (evt) {
      evt.preventDefault();
      dropzone.classList.remove("is-dragover");
      var files = evt.dataTransfer && evt.dataTransfer.files;
      if (files && files.length) {
        input.files = files;
        showFile(files[0]);
      }
    });
  }

  function setupSubmitOverlay() {
    var form = document.querySelector("#evaluation-form");
    var overlay = document.querySelector("#loading-overlay");
    var submitBtn = document.querySelector("#submit-btn");
    if (!form || !overlay) return;

    form.addEventListener("submit", function (evt) {
      var repoUrl = form.querySelector('[name="repo_url"]');
      var docTexte = form.querySelector('[name="documentation_texte"]');
      var docLien = form.querySelector('[name="documentation_lien"]');
      var docFichier = form.querySelector('[name="documentation_fichier"]');

      var rempli =
        (repoUrl && repoUrl.value.trim()) ||
        (docTexte && docTexte.value.trim()) ||
        (docLien && docLien.value.trim()) ||
        (docFichier && docFichier.files && docFichier.files.length);

      if (!rempli) {
        evt.preventDefault();
        window.alert(
          "Indiquez l'URL d'un dépôt GitHub, ou une documentation (fichier, lien ou texte collé)."
        );
        return;
      }

      overlay.classList.add("is-visible");
      if (submitBtn) submitBtn.disabled = true;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupDocTabs();
    setupDropzone();
    setupSubmitOverlay();
  });
})();
