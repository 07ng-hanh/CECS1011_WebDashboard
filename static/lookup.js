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
        }, params: {
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

async function promptDiscardBatch(batch_id) {
    let reason = prompt("Reason for discarding this batch")

    if (reason === "" || reason == null) {
        alert("Failed to discard batch: Cancelled or empty reason.")
        return
    }

    let r = await axios.delete("/api/batch/discard-batch", {
        validateStatus: function (status) {
            return status >= 200 && status <= 500
        }, params: {
            batch_id: batch_id, reason: reason
        }
    })
    if (r.status === 200) {
        alert("Discard done!")
        await debounceSearch(0)
    } else {
        alert("Discarding failed: Error" + r.status)
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
        weight.innerHTML = `Weight: <b>${v.weight.toFixed(3)} kg</b>`

        let importDate = document.createElement("p")
        importDate.className = "card-info-entry"
        importDate.innerHTML = `Harvested At: <b>${new Date(v.import_date).toLocaleDateString()}</b>`

        let expiration = document.createElement("p")
        expiration.className = "card-info-entry"
        let date_diff = Math.round((v.exp_date - (new Date()).getTime()) / 86400000)
        let expired = false
        if (date_diff <= 0) {
            expiration.innerHTML = `Expired At: <b style="color: red">${new Date(v.exp_date).toLocaleDateString()}</b>`
            card.style.borderColor = "rgba(255, 0, 0, 1)"
            card.style.borderWidth = "2px"
            expired = true
        } else if (date_diff < 20) {
            expiration.innerHTML = `Expires At: <b style="color: red">${new Date(v.exp_date).toLocaleDateString()}</b> <span style="color: red">(${date_diff} days)</span>`
            card.style.backgroundColor = "rgba(255, 255, 0, 0.5)"
        } else {
            expiration.innerHTML = `Expires At: <b>${new Date(v.exp_date).toLocaleDateString()}</b> (${date_diff} days)`
        }

        let status = document.createElement("p")
        status.className = "card-info-entry"
        // Check status

        if (v.is_in_warehouse && v.assigned_order_no == null) {
            if (expired) {
                status.innerHTML = "Status: <b class='accented-indicator' style='color: gray'>Expired, please discard.</b>"
            } else {
                status.innerHTML = "Status: <b class='accented-green'>Available</b>"
            }
        } else if (v.is_in_warehouse && v.assigned_order_no != null) {
            // TODO: Add URL to order here
            // Warn against exporting expired stuff.

            if (expired) {
                status.innerHTML = `Status: <b class='accented-danger' style="color: gray">Expired, please remove from order <a style="text-decoration: underline;">${v.assigned_order_no}</a>.</b>`
            } else {
                status.innerHTML = `Status: <b class='accented-purple'>Marked for Export <a style="text-decoration: underline;">(Order ${v.assigned_order_no})</a></b>`
            }

        } else if (!v.is_in_warehouse && v.assigned_order_no != null) {
            status.innerHTML = `Status: <b class="accented-purple" style="color: gray">Exported</b>`
            // When an item is exported, we dont track its expiration anymore
            expiration.style.display = "none"
        } else if (v.discard_reason != null && !v.is_in_warehouse) {
            status.innerHTML = `Status: <b class="accented-danger" style="color: gray">Discarded (${v.discard_reason})</b>`
            // Same for discarded items
            expiration.style.display = "none"
        }

        // Append the action sidebar
        let entryCardActionBtnGroup = document.createElement("div")
        entryCardActionBtnGroup.className = "entry-card-action-btn"

        if (v.is_in_warehouse && !expired) {
            let assignToBtn = document.createElement("button")
            assignToBtn.className = "btn btn-outline-primary"
            assignToBtn.innerText = "Assign Shipment"
            entryCardActionBtnGroup.appendChild(assignToBtn)
        }


        let batchHealth = document.createElement("button")
        batchHealth.innerText = "Health"
        batchHealth.className = "btn btn-outline-primary"
        entryCardActionBtnGroup.appendChild(batchHealth)


        if (v.is_in_warehouse) {
            let discardBtn = document.createElement("button")
            discardBtn.innerText = "Discard"
            discardBtn.className = "btn btn-outline-danger"
            discardBtn.addEventListener("click", async () => {
                await promptDiscardBatch(v.batch_id)
            })

            entryCardActionBtnGroup.appendChild(discardBtn)
        }

        cardInfo.appendChild(idTag)
        cardInfo.appendChild(produceDescription)
        cardInfo.appendChild(weight)
        cardInfo.appendChild(importDate)
        cardInfo.appendChild(expiration)
        cardInfo.appendChild(status)
        card.className = "entry-card"

        card.appendChild(cardInfo)
        card.appendChild(entryCardActionBtnGroup)
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
    let params = new URLSearchParams(document.location.search)
    let id = params.get('id')
    let r = null
    if (id) {
        document.getElementById("produce-name").value = id
        r = await searchWithFilters(false)
    } else {
        r = await warehouseSearch()
    }
    showSearchResults(r)
})

async function searchWithFilters(show_results = true) {
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

    if (Number.isNaN(date_from_utc_timestamp)) {
        date_from_utc_timestamp = undefined
    }

    if (Number.isNaN(date_to_utc_timestamp)) {
        date_to_utc_timestamp = undefined
    }

    let r = await warehouseSearch(q, date_from_utc_timestamp, date_to_utc_timestamp, status, sortBy, sortAscending, almostExpiredOnly)
    if (show_results) {
        showSearchResults(r)
    } else {
        return r
    }

}

let debounce_timer_id = undefined

async function debounceSearch(timeout = 1) {
    if (debounce_timer_id) {
        clearTimeout(debounce_timer_id)
        debounce_timer_id = undefined
    }
    debounce_timer_id = setTimeout(async () => {
        await searchWithFilters()
    }, timeout)
}

async function exportToXLSX(export_all = false) {
    let r = undefined
    if (export_all) {
        r = await warehouseSearch()
    } else {
        r = await searchWithFilters(false)
    }

    let rows = ["Batch ID, Harvest Type Name, Quantity, Weight (kg), Harvest Date, Expiration Date, Export Date (if any), In Stock?, Assigned Shipment No. (if any)".split(', '),]
    r.forEach((entry) => {

        let export_date_str = null
        if (entry.export_date != null) {
            export_date_str = new Date(entry.export_date).toLocaleDateString()
        }

        rows.push([entry.batch_id.toString(), entry.harvest_type_name, entry.quantity, entry.weight.toFixed(3), new Date(entry.import_date).toLocaleDateString(), new Date(entry.exp_date).toLocaleDateString(), export_date_str, entry.is_in_warehouse, entry.assigned_order_no])
    })

    let xlsx_out = XLSX.utils.aoa_to_sheet(rows)
    let wb = XLSX.utils.book_new(xlsx_out)

    XLSX.writeFile(wb, "xlsx-out.xlsx")

}

async function exportToCSV(export_all = false) {
    let r = undefined
    if (export_all) {
        r = await warehouseSearch()
    } else {
        r = await searchWithFilters(false)
    }

    let rows = ["Batch ID, Harvest Type Name, Quantity, Weight (kg), Harvest Date, Expiration Date, Export Date (if any), In Stock?, Assigned Shipment No. (if any)",]
    r.forEach((entry) => {
        let export_date_str = null
        if (entry.export_date != null) {
            export_date_str = new Date(entry.export_date).toLocaleDateString()
        }
        rows.push(`${entry.batch_id.toString()}, ${entry.harvest_type_name}, ${entry.quantity}, ${entry.weight.toFixed(3)}, ${new Date(entry.import_date).toLocaleDateString()}, ${new Date(entry.exp_date).toLocaleDateString()}, ${export_date_str}, ${entry.is_in_warehouse}, ${entry.assigned_order_no}`)

    })

    let file = new Blob([rows.join("\n")], {type: 'text/csv'})
    let downloadLink = document.createElement("a")
    downloadLink.href = window.URL.createObjectURL(file)
    downloadLink.click()
}