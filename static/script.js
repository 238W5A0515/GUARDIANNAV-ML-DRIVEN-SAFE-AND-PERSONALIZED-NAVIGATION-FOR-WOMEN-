function geocode(address, latInputId, lonInputId) {
    return $.ajax({
        url: '/geocode',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ address: address }),
        success: function (response) {
            document.getElementById(latInputId).value = response.lat;
            document.getElementById(lonInputId).value = response.lon;
        },
        error: function () {
            alert('Failed to geocode address: ' + address);
        }
    });
}

$('#routeForm').on('submit', async function (event) {
    event.preventDefault();

    const startAddress = $('#startAddress').val();
    const endAddress = $('#endAddress').val();

    await geocode(startAddress, 'start_lat', 'start_lon');
    await geocode(endAddress, 'end_lat', 'end_lon');

    this.submit();
});
