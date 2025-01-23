/* When the user clicks on the button,
toggle between hiding and showing the dropdown content */

document.getElementById(
    'down-button').addEventListener('click', (e) => {
        window.parent.location.reload();
        console.log("down-button has been clicked");
    });
