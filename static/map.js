/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

var moveDown = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Drilling down to "+type+ " set within "+ area, '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;
      };
var moveUp = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Moving up to "+ area + " "+ type+ " level ", '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;

      };
var showMore = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Showing the "+type+ " set within "+ area, '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;

      };
var layerUpdate = function () {
  // Send a message to the parent
      window.parent.postMessage("Updating Layer Data.", '*');
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = ul.scrollHeight;
      };

function highlightNumber(selector) {
    document.querySelectorAll(selector).forEach(element => {
        let text = element.innerHTML;
        let match = text.match(/\d+/); // Find the first number in the text

        if (match) {
            let highlighted = `<span class="highlight">${match[0]}</span>`;
            element.innerHTML = text.replace(match[0], highlighted); // Replace number with highlighted version
        }
    });
}

highlightNumber("leaflet-marker-icon leaflet-div-icon leaflet-zoom-animated leaflet-interactive");
