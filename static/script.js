function updateMatchOptions() {
    var seriesId = document.getElementById("series_id").value;

    // Make an AJAX request to retrieve the match_ids based on the selected series_id
    fetch(`/get_match_ids?series_id=${seriesId}`)
        .then(response => response.json())
        .then(matchIds => {
            var matchIdDropdown = document.getElementById("match_id");
            matchIdDropdown.innerHTML = "";

            for (var i = 0; i < matchIds.length; i++) {
                var option = document.createElement("option");
                option.text = matchIds[i];
                option.value = matchIds[i];
                matchIdDropdown.appendChild(option);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}