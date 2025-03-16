/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

var moveDown = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Drilling down to "+type+ " set within "+ area, '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = 0;
      };
var moveUp = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Moving up to "+ area + " "+ type+ " level ", '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = 0;
      };
var showMore = function (msg,area, type) {
  // Send a message to the parent
      window.parent.postMessage("Showing the "+type+ " set within "+ area, '*');
      window.location.assign(msg);
      var ul = parent.document.getElementById("logwin");
      ul.scrollTop = 0;
      };

async function displayXURL(url) {
  try {
    const response = await fetch(url);
 	if (!response.ok) {
    console.log(`URL does not exist: ${url}`);
    let pristineurl = url.replace("PRINTX.html", "PRINT.html");
    alert(pristineurl);
    window.location.assign(pristineurl);
    return
 }
 else {
   console.log(`URL exists: ${url}`);
   alert(url);
   window.location.assign(url);
 }
  } catch (error) {
    console.log(`Error checking URL: ${error}`);
  }
};
