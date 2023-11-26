// Define constants
const letters = "ABCDEFGNOPQRSTUVWXYZ";

// Fade in Spyfall title
var textWrapper = document.querySelector('.ml3');
textWrapper.innerHTML = textWrapper.textContent.replace(/\S/g, "<span class='letter'>$&</span>");

// Animation to fade in 'Spyfall' text
anime.timeline({loop: false})
.add({
    targets: '.ml3 .letter',
    opacity: [0,1],
    easing: "easeInOutQuad",
    duration: 2250,
    delay: (el, i) => 150 * (i+1)
});