function updateMatchOptions() {
    var yearDropdown = document.getElementById("year");
    var year = yearDropdown.value;

    fetch('/get_match_ids?year=' + year)
        .then(response => response.json())
        .then(data => {
            var matchIdDropdown = document.getElementById("match_name");
            matchIdDropdown.innerHTML = "";

            data.forEach(matchId => {
                var option = document.createElement("option");
                option.text = matchId;
                option.value = matchId;
                matchIdDropdown.appendChild(option);
            });0
        });
}