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

    harvest_date_range_picker.on('selected', debounceSearch)

    let produce_name_inputbox = document.getElementById("produce-name")
    produce_name_inputbox.focus()

})

async function warehouseSearch(q = "", harvest_timestamp_from, harvest_timestamp_to, status, sortBy, sortAscending, almostExpiredOnly = false) {
    let r = await axios.get("/api/batch/list-batches", {
        validateStatus: function (status) {
                return status >= 200 && status <= 500
        },
        params: {
            name_or_id_query: q,
            harvest_timestamp_from: harvest_timestamp_from,
            harvest_timestamp_to: harvest_timestamp_to,
            status: status,
            sortBy: sortBy,
            sortAscending: sortAscending,
            almostExpiredOnly: almostExpiredOnly
        }

    })
    if (r.status === 200) {
        return r.data
    } else {
        alert("Cannot fetch batch list. Please try again.")
    }
}

function showSearchResults(r) {

    let container = document.querySelector("div.card-container")
    container.innerHTML = ""

    r.forEach((v) => {
        let card = document.createElement("div")
        let cardInfo = document.createElement("div")
        cardInfo.className = "card-info"

        // Populating cardInfo
        let idTag = document.createElement("p")
        idTag.className = "card-info-entry"
        idTag.innerText = `ID: ${v.batch_id}`
        idTag.style.color = "gray"

        let produceDescription = document.createElement("p")
        produceDescription.className = "card-info-entry"
        produceDescription.innerHTML = `<b>${v.harvest_type_name} (${v.quantity} units)</b>`

        let weight = document.createElement("p")
        weight.className = "card-info-entry"
        weight.innerHTML = `Weight: <b>${v.weight.toFixed(2)} kg</b>`

        let importDate = document.createElement("p")
        importDate.className = "card-info-entry"
        importDate.innerHTML = `Imported At: <b>${new Date(v.import_date).toLocaleDateString()}</b>`

        let expiration = document.createElement("p")
        expiration.className = "card-info-entry"
        let date_diff = Math.round((v.exp_date - v.import_date) / 86400000)

        if (date_diff > 20) {
            expiration.innerHTML = `Expires At: <b>${new Date(v.exp_date).toLocaleDateString()}</b> (${date_diff} days)`
        } else {
            expiration.innerHTML = `Expires At: <b style="color: red">${new Date(v.exp_date).toLocaleDateString()}</b> <span style="color: red">(${date_diff} days)</span>`
        }


        let status = document.createElement("p")
        status.className = "card-info-entry"
        // Check status
        if (v.is_in_warehouse && v.assigned_order_no == null ) {
            status.innerHTML = "Status: <b class='accented-green'>Available</b>"
        } else if (v.is_in_warehouse && v.assigned_order_no != null) {
            // TODO: Add URL to order here
            status.innerHTML = `Status: <b class='accented-purple'>Marked for Export <a style="text-decoration: underline;">(Order ${v.assigned_order_no})</a></b>`
        } else if (!v.is_in_warehouse && v.assigned_order_no != null) {
            status.innerHTML = `Status: <b class="accented-purple" style="color: gray">Exported</b>`
        } else if (v.discard_reason != null && !v.is_in_warehouse) {
            status.innerHTML = `Status: <b class="accented-danger" style="color: gray">Discarded (${v.discard_reason})</b>`
        }

        cardInfo.appendChild(idTag)
        cardInfo.appendChild(produceDescription)
        cardInfo.appendChild(weight)
        cardInfo.appendChild(importDate)
        cardInfo.appendChild(expiration)
        cardInfo.appendChild(status)
        card.className = "entry-card"

        card.appendChild(cardInfo)
        container.appendChild(card)
    })
}

async function clearFilters() {
    document.getElementById("produce-name").value = ""
    document.getElementById("harvest-date-range").value = ""
    document.getElementById("status-dropdown").value = ""
    document.getElementById("sort-dropdown").value = ""
    document.getElementById("sort-direction").value = "ascending"

    let r = await warehouseSearch()
    showSearchResults(r)
}

document.addEventListener("DOMContentLoaded", async () => {
    let r = await warehouseSearch()
    showSearchResults(r)
})

async function searchWithFilters() {
    let q = document.getElementById("produce-name").value
    let harvestRange = document.getElementById("harvest-date-range").value
    let status = document.getElementById("status-dropdown").value
    let sortBy = document.getElementById("sort-dropdown").value
    let sortAscending = document.getElementById("sort-direction").value === "ascending"
    let almostExpiredOnly = document.getElementById("almost-expire-toggle").checked

    // Extract millisecond timestamp
    let date_from = harvestRange.split(" - ")[0]
    let date_to = harvestRange.split(" - ")[1]

    let date_from_utc_timestamp = (new Date(date_from)).getTime()
    let date_to_utc_timestamp = (new Date(date_to)).getTime()

    if ( Number.isNaN(date_from_utc_timestamp)) {
        date_from_utc_timestamp = undefined
    }

    if (Number.isNaN(date_to_utc_timestamp)) {
        date_to_utc_timestamp = undefined
    }

    let r = await warehouseSearch(q, date_from_utc_timestamp, date_to_utc_timestamp, status, sortBy, sortAscending, almostExpiredOnly)
    showSearchResults(r)
}

let debounce_timer_id = undefined
async function debounceSearch(timeout = 1) {
    if (debounce_timer_id) {
        clearTimeout(debounce_timer_id)
        debounce_timer_id = undefined
    }
    debounce_timer_id = setTimeout(
        async () => {
            await searchWithFilters()
        }, timeout
    )
}