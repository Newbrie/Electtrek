/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

var moveDown = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Fetching the "+type+ " set within "+ area, '*');
      window.location.assign(msg);
      alert(msg+"::"+type+" "+area);
      };

function chgAction( action_name , area, type) {
        alert("chgAction called");
        element = document.getElementsByName('search-theme-form');
        element.action = action_name;
        window.parent.postMessage("Fetching the "+type+ " set within "+ area, '*');
        window.location.assign(action_name);
        alert(action_name+"::"+type+" "+area);
    };
