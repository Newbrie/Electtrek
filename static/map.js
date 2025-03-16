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

function displayXURL(url) {
    fetch(url, { method: 'HEAD' })
        .then(response => {
            if (response.ok) {
                let script = document.createElement('script');
                script.src = url;
                alert("Exists:"+ script.src)
                document.body.appendChild(script);
            } else {
                let script = document.createElement('script');
                script.src = url.replace("PRINTX.html", "PRINT.html");
                alert("NoExists:"+ script.src)
                document.body.appendChild(script);
            }
        })
        .catch(() => {
            let script = document.createElement('script');
            script.src = url.replace("PRINTX.html", "PRINT.html");
            alert("Error:"+ script.src)
            document.body.appendChild(script);
        });

    return false; // Prevent default action
};
