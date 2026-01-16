let port_name_list = ["AA"]
let produce_types = ["a"]
let departure_date_picker = undefined
let page = 1

async function fetch_shipments(id, from, to, departure_start_int, departure_end_int, prod_type, status, sort, sort_ascending, page) {
    let resp = await axios.get("/api/shipments/list-shipments", {
        params: {

        },
        validateStatus: function (status) {
            return status >= 200 && status <= 500
        }
    })
}

async function handle_fetch_shipments() {
//     get inputs
    let shipment_id = document.getElementById("shipment-id").value
    let from = document.getElementById("loc-from").value
    let to = document.getElementById("loc-to").value
    let departure_start = departure_date_picker.getStartDate().getTime()
    let departure_end = departure_date_picker.getEndDate().getTime()
    let status = document.getElementById("status").value
    let prod_type = document.getElementById("export-type").value
    let sort_by = document.getElementById("sort-by").value
    let sort_ascending =document.getElementById("sort-direction").value === "ascending"

    const r = await fetch_shipments(shipment_id, from, to, departure_start, departure_end, prod_type, status, sort_by, sort_ascending, page)
}

document.addEventListener("DOMContentLoaded", () => {
    departure_date_picker = new Litepicker({
        element: document.getElementById("export-date"),
        mobileFriendly: true,
        // format: "YYYY-MM-DD",
        singleMode: false,
        useResetBtn: true,
        buttonText: {
            reset: "Reset"
        },
    })

    departure_date_picker.getStartDate()

    let port_from = document.getElementById("loc-from")

    // Autofocus on port_from
    port_from.focus()
})

