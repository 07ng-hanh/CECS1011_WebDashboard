let lst = ["awk"]
let harvest_date_range_picker = undefined

document.addEventListener("DOMContentLoaded", () => {

    //     Integrate range-based datepicker with the harvest date range input field
    harvest_date_range_picker = new Litepicker({
        element: document.getElementById("harvest-date-range"),
        mobileFriendly: true,
        format: "YYYY-MM-DD",
        singleMode: false,
        useResetBtn: true,
        buttonText: {
            reset: "Reset"
        },
    })

    // Make Awesomeplete autocomplete bubble open on product search box focused -->
    let produce_name_inputbox = document.getElementById("produce-name")
    console.log(produce_name_inputbox)
    let produce_name_autocomplete = new Awesomplete(produce_name_inputbox, {
        minChars: 0,
        maxItems: 15,
        list: lst
    })
    console.log(produce_name_autocomplete)
    produce_name_autocomplete.evaluate()
    produce_name_autocomplete.close()
    produce_name_inputbox.addEventListener("focus", () => {
        console.log("focused")
        produce_name_autocomplete.open()
    })

    produce_name_inputbox.focus()

})


