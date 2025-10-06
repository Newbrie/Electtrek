<script>
function incrementVoteCount(button) {
    let count = parseInt(button.getAttribute("data-count")) || 0;
    let max = parseInt(button.getAttribute("data-max")) || 1;
    count = (count + 1) % (max + 1);
    button.setAttribute("data-count", count);
    button.innerText = count + "/" + max;

    const row = button.closest("tr");
    row.style.backgroundColor = count > 0 ? "#d4edda" : "";
}

function updateMaxVote(selectEl) {
    const max = parseInt(selectEl.options[selectEl.selectedIndex].getAttribute("data-max")) || 1;
    const row = selectEl.closest("tr");
    const button = row.querySelector("button");
    button.setAttribute("data-max", max);
    button.setAttribute("data-count", 0);
    button.innerText = "0/" + max;
    row.style.backgroundColor = "";
}
</script>
