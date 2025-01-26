/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

var moveDown = function (msg) {
  // Send a message to the parent
      window.parent.postMessage("Fetching data about "+ msg, '*');
      alert("sent:"+msg);
      window.location.assign() = msg;
      };
