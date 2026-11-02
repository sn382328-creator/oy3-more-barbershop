
/* =====================================================
   OY3 MORE BARBERSHOP
   MAIN JAVASCRIPT FILE
   ===================================================== */


/* 1. AUTOMATIC HAIRCUT PRICE DISPLAY */

document.addEventListener("DOMContentLoaded", function () {

    const serviceInput = document.getElementById("service");
    const priceDisplay = document.getElementById("selected-price");

    const prices = {
        "Low Cut": 30,
        "Skin Fade": 40,
        "Low Fade": 35,
        "Mid Fade": 40,
        "High Fade": 40,
        "Burst Fade": 45,
        "Taper Fade": 35,
        "Afro": 40,
        "Waves": 40,
        "Mohawk": 45,
        "Buzz Cut": 30,
        "Crew Cut": 30,
        "Beard Trim": 15,
        "Haircut and Beard": 50
    };

    if (serviceInput && priceDisplay) {

        serviceInput.addEventListener("input", function () {

            const selectedService = serviceInput.value.trim();

            if (prices[selectedService] !== undefined) {

                priceDisplay.textContent =
                    "YOUR HAIRCUT PRICE: GH₵" + prices[selectedService];

            } else if (selectedService === "") {

                priceDisplay.textContent =
                    "Select a hairstyle to see your price.";

            } else {

                priceDisplay.textContent =
                    "Price not available. Please contact the barber.";

            }

        });

    }


    /* 2. PREVENT PAST APPOINTMENT DATES */

    const dateInput = document.getElementById("date");

    if (dateInput) {

        const today = new Date();

        const localDate = new Date(
            today.getTime() - today.getTimezoneOffset() * 60000
        ).toISOString().split("T")[0];

        dateInput.min = localDate;

    }


    /* 3. ADMIN APPOINTMENT SEARCH */

    const searchInput = document.getElementById("bookingSearch");

    if (searchInput) {

        searchInput.addEventListener("input", function () {

            const searchValue = this.value.toLowerCase();

            const appointments =
                document.querySelectorAll(".appointment-card");

            appointments.forEach(function (card) {

                const bookingDetails = card.textContent.toLowerCase();

                card.style.display =
                    bookingDetails.includes(searchValue) ? "" : "none";

            });

        });

    }


    /* 4. BOOKING FORM VALIDATION */

    const bookingForm = document.querySelector(".appointment-form");

    if (bookingForm) {

        bookingForm.addEventListener("submit", function (event) {

            const selectedService =
                document.getElementById("service").value.trim();

            if (prices[selectedService] === undefined) {

                event.preventDefault();

                alert("Please select a valid hairstyle from our price list.");

            }

        });

    }


    /* 5. MOBILE MENU ENHANCEMENT */

    const navigationLinks =
        document.querySelectorAll(".main-nav a");

    navigationLinks.forEach(function (link) {

        link.addEventListener("click", function () {

            console.log("Navigation link selected.");

        });

    });

});
