/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

var moveDown = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Drilling down to "+type+ " set within "+ area, '*');
      window.location.assign(msg);
      };
var showMore = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Showing the "+type+ " set within "+ area, '*');
      window.location.assign(msg);
      };
