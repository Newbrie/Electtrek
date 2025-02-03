{% extends "Dash0.html" %}
// Listen to message from child window

const pessages = [];
var pack = JSON.parse('{{ get_flashed_messages()|tojson|safe }}');

for (let x in pack) {
pessages.push(pack[x]);
};

var iframeEl = document.getElementsByName('iframe1');

function bindEvent( element, eventName, eventHandler) {
 if (element.addEventListener){
     element.addEventListener(eventName, eventHandler, false);
 } else if (element.attachEvent) {
     element.attachEvent('on' + eventName, eventHandler);
 };
};

bindEvent( window, 'message', function (e) {
  pessages.pop();
  pessages.push(e.data);
  var ul = document.getElementById("logwin");
  var li = document.createElement("li");
  li.appendChild(document.createTextNode(e.data));
  ul.appendChild(li);
  alert("_____onmessage: "+e.data);
});

function updateMessages(){
old = pessages.pop();
var ul = parent.document.getElementById("logwin");
var li = parent.document.createElement("li");
li.appendChild(parent.document.createTextNode(old+":completed"));
ul.appendChild(li);
var tab = parent.document.getElementById("data-table");
tab.focus();
alert(tab.id);

};
