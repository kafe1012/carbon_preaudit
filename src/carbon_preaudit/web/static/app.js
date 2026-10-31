// Leaflet map for the result fragment and the swap rule for error responses. No build step.
(function () {
  "use strict";

  function initMap(root) {
    var el = root.querySelector("#map");
    var data = root.querySelector("#polygon-data");
    if (!el || !data || typeof L === "undefined") {
      return;
    }
    var map = L.map(el);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
    var layer = L.geoJSON(JSON.parse(data.textContent)).addTo(map);
    map.fitBounds(layer.getBounds());
  }

  // htmx does not swap 4xx responses by default; the 422 body is the readable error message.
  document.addEventListener("htmx:beforeSwap", function (event) {
    if (event.detail.xhr.status === 422) {
      event.detail.shouldSwap = true;
      event.detail.isError = false;
    }
  });

  // afterSettle, not afterSwap: htmx settles attributes of elements whose id survives the swap
  // (#map on a second check) and would strip the classes Leaflet has just added.
  document.addEventListener("htmx:afterSettle", function (event) {
    initMap(event.detail.target);
  });
})();
