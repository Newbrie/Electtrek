/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

function reftag(url) {
  console.log("down-button has been clicked");
  window.parent.location.href = "http://127.0.0.1:5000/map/UNITED_KINGDOM/ENGLAND/ENGLAND-MAP.html";

    };
// Send a message to the parent
var sendMessage = function (msg) {
    // Make sure you are sending a string, and to stringify JSON
    window.parent.postMessage(msg, '*');
    alert("sent:"+msg);

};
