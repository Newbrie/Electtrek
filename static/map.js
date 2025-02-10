/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

var moveDown = function (msg,area) {
  // Send a message to the parent
      window.parent.postMessage("Fetching data about "+ area, '*');
      window.location.assign(msg);
      alert(msg+"::"+area);
      };

function chgAction( action_name ) {
        document.search-theme-form.action = action_name;
    };
