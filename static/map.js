/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

var moveDown = function (msg,area) {
  // Send a message to the parent
      const pessages = [];
      var pack = JSON.parse('{{ get_flashed_messages()|tojson|safe }}');

      for (let x in pack) {
        pessages.push(pack[x]);
      };
      window.parent.postMessage("Fetching data about "+ pessages, '*');
  
      window.parent.postMessage("Fetching data about "+ area, '*');
      window.location.assign(msg);
      };
