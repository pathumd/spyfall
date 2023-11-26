// Force page refresh if lobby was accessed from history (via back/forward arrow)
var perfEntries = performance.getEntriesByType("navigation");
if (perfEntries[0].type === "back_forward") {
    location.reload();
}

// Notify all other users in game that you've joined the lobby
socket.emit("join", {'playerName': detectiveName, 'channel': gameCode})

// Handler for updating lobby with joining players
socket.on('playerJoinLog', data => {
    console.log(data["message"] + " joined");

    if (playerList.includes(data["message"]) == false) {
        // Generate an (h1) element for new player
        let newPlayerName = document.createElement('H1')
        newPlayerName.innerText = data["message"]
        newPlayerName.classList.add('player-name')
        $('.players').append(newPlayerName)
        playerList.push(newPlayerName);
    }
});

// Handler to send request to backend to assign player a role (and location)
socket.on('gameStarting', data => {
    console.log(data["gameCode"] + " is starting...");
    let dataToSend = {'playerName': detectiveName, 'location': data["location"], 'channel': gameCode}
    // Send POST request to get role (and location) assigned by backend
    $.ajax({
        url: '/get_game_info',
        type: 'POST',
        data: JSON.stringify(dataToSend),
        contentType: "application/json",
        dataType: 'json',
        success: function (response) {
            console.log("Request succeeded for " + detectiveName)
            if (response.redirect) {
                // If role (and location) was assigned, go to /<gameCode>/play route to start playing
                window.location.href = response.redirect;
            }
        },
        error: function (response) {
            console.log("Request failed for " + detectiveName);
        }
    });
});

// Handler to show alert message that game has ended (i.e. game owner ended game)
socket.on('game_ended', data => {
    $("#game-ended-message").show();
});

// Handler for updating lobby when players leave game/lobby
socket.on('playerLeft', data => {
    var playerName = data["message"];
    var playerList = document.getElementById('playerList').children;
    for (let i = 0; i < playerList.length; i++) {
        if ((playerList[i].innerText).localeCompare(playerName) == 0) {
            // Remove player that has matching name with the player that left
            playerList[i].remove();
        }
    }
});

function copyGameCode() {
    // Copies the game code to the user's clipboard
    navigator.clipboard.writeText(gameCode);
    alert("Game code copied!");
}

function startGame() {
    // Game owner will be responsible for assigning roles to all 
    // players (including themselves) and selecting a random location.
    socket.emit("organizeGame", {'channel': gameCode})
}