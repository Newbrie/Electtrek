/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

var moveDown = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Fetching the "+type+ " set within "+ area, '*');
      window.location.assign(msg);
      };
