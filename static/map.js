/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

function reftag(url) {
  console.log("down-button has been clicked");
  window.parent.location.href = "http://127.0.0.1:5000/map/UNITED_KINGDOM/ENGLAND/ENGLAND-MAP.html";

    };
    // addEventListener support for IE8
function bindEvent(element, eventName, eventHandler) {
   if (element.addEventListener) {
       element.addEventListener(eventName, eventHandler, false);
   } else if (element.attachEvent) {
       element.attachEvent('on' + eventName, eventHandler);
   }
}

// Send a message to the parent
var sendMessage = function (msg) {
   // Make sure you are sending a string, and to stringify JSON
   window.parent.postMessage("msg", '*');
};

var results = document.getElementById('results');
var messageButton = document.getElementById('message_button');

// Listen to messages from parent window
bindEvent(window, 'message', function (e) {
   results.innerHTML = e.data;
});

// Send random message data on every button click
bindEvent(messageButton, 'click', function (e) {
   var random = Math.random();
   sendMessage('' + random);
});
