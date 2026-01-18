let port_name_list = ["AA"]
let produce_types = ["a"]
let departure_date_picker = undefined
let page = 1

let prod_id = undefined
let batch_exp_date = undefined
let batch_id = undefined
const status = "status-waiting"


async function flipPage(f) {
    page += f
    if (page < 1) {
        page = 1
    }
    document.getElementById("pageCnt").innerText = page.toString()
    await handle_fetch_shipments()
}

async function assign_to_shipment(shipment_id) {
    r = await axios.post(`/api/batch/assign-order-to-batch?batch_id=${batch_id}&order_id=${shipment_id}`)

    if (r.status !== 200) {
        alert("Assignment failed. Error: " + r.status)
    } else {
        alert("Assignment successful.")
        window.opener.searchWithFilters(true)
        window.close()
    }


}

async function unassign_from_current() {
    r = await axios.delete(`/api/batch/remove-order-from-batch?batch_id=${batch_id}`)
    if (r.status !== 200) {
        alert("Unassignment failed. Error: " + r.status)
    } else {
        alert("Unassignment successful.")
        window.opener.searchWithFilters(true)
        window.close()
    }
}

function get_localtime_iso_string(date = new Date()) {
    return `${date.getFullYear()}-${(date.getMonth()+1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`
}

function show_shipments(shipments) {
    const container = document.getElementById("orders-card-container")
    container.innerHTML = ""

    if (shipments.length === 0) {
        container.innerHTML = "<h2>No Shipments Available</h2>"
        return
    }


    shipments.forEach((shipment) => {
        const card = document.createElement("div")
        const infoCard = document.createElement("div")
        const idLbl = document.createElement("p")
        idLbl.innerText = 'ID: ' + shipment.shipment_id
        idLbl.style.color = 'gray'

        const routeLbl = document.createElement("p")
        routeLbl.innerHTML = `<b>${shipment.source_port_name}</b> <span style="color: gray">${shipment.source_port_id}</span> <i class="bi-arrow-right"></i> <b >${shipment.dest_port_name}</b> <span style="color: gray">${shipment.dest_port_id}</span>`

        const orderLbl = document.createElement("p")
        orderLbl.innerHTML = `Produce: <b>${shipment.produce_type_name}</b> (<b>${shipment.produce_qty}</b> units)`

        const qtyLbl = document.createElement("p")
        qtyLbl.innerHTML = `Quantity: <b>${shipment.produce_qty}</b> units`

        const scheduleLbl = document.createElement("p")
        scheduleLbl.innerHTML = `Scheduled Departure: <b>${get_localtime_iso_string(new Date(shipment.planned_departure_timestamp))}</b> (ETA: <b>${Math.ceil(shipment.eta_milliseconds / 86400 / 1000)} days</b>)`

        const fulfilledProg = document.createElement("p")
        fulfilledProg.innerHTML = `Fulfilled: <progress value="${shipment.cur_quantity}" max="${shipment.produce_qty}"></progress> ${shipment.cur_quantity} / ${shipment.produce_qty}`

        const batches = document.createElement("p")
        batches.style.display = 'flex'
        batches.style.gap = '5px'
        const batchesLbl = document.createElement("p")
        batchesLbl.innerText = 'Batches:'
        batches.appendChild(batchesLbl)
        if (shipment.batches.length === 0) {
            const noneTag = document.createElement("p")
            noneTag.style.color = 'grey'
            noneTag.innerText = 'None'
            batches.appendChild(noneTag)
        } else {
            shipment.batches.forEach((batchID) => {
                const batchTag = document.createElement("a")
                batchTag.innerText = "#" + batchID.toString()
                batchTag.style.background = '#007bff22'
                batchTag.style.borderRadius = '15px'
                batchTag.style.paddingLeft = '5px'
                batchTag.style.paddingRight = '5px'

                batchTag.href = `lookup.html?id=${batchID}`

                batches.appendChild(batchTag)
            })
        }

        const status = document.createElement("p")
        let isSafe = true
        if (shipment.planned_departure_timestamp > new Date().getTime()) {
            if (shipment.planned_departure_timestamp + shipment.eta_milliseconds < batch_exp_date) {
                status.innerHTML = "Status: <b class='accented-green'>Safe to export</b>"
            } else {
                status.innerHTML = "Status: <b class='accented-danger'>Can't export - Shipment duration exceeds batch lifespan</b>"
                isSafe = false
            }
        } else {
            if (new Date().getTime() + shipment.eta_milliseconds < batch_exp_date) {
                status.innerHTML = "Status: <b class='accented-purple'>Unsafe - Late shipment, may require immediate departure</b>"
            } else {
                status.innerHTML = "Status: <b class='accented-danger'>Can't export - Shipment duration exceeds batch lifespan</b>"
                isSafe = false
            }
        }


        // button set
        const btnSet = document.createElement("div")
        btnSet.className = "orders-card-btn"
        const primaryActionBtn = document.createElement("button")
        primaryActionBtn.onclick = async (ev) => {await assign_to_shipment(shipment.shipment_id)}
        primaryActionBtn.className = "btn btn-outline-primary"

        btnSet.appendChild(primaryActionBtn)

        if (shipment.cur_quantity < shipment.produce_qty) {
            primaryActionBtn.innerText = "Select"
        } else if (shipment.actual_departure_timestamp == null) {
            primaryActionBtn.innerText = "Begin Export"
        } else {
            primaryActionBtn.style.display = 'none'
        }

        if (!isSafe) {
            primaryActionBtn.disabled = true
            primaryActionBtn.className = "btn btn-outline-secondary"
        }

        infoCard.className = "orders-card-info"
        card.className = "orders-card"

        infoCard.appendChild(idLbl)
        infoCard.appendChild(routeLbl)
        infoCard.appendChild(orderLbl)
        infoCard.appendChild(scheduleLbl)
        infoCard.appendChild(fulfilledProg)
        infoCard.appendChild(batches)
        infoCard.appendChild(status)



        card.appendChild(infoCard)
        card.appendChild(btnSet)
        container.appendChild(card)



    })

}


async function fetch_shipments(id, from, to, departure_start_int, departure_end_int, prod_type, status, sort, sort_ascending, page) {
    let resp = await axios.get("/api/shipments/list-shipments", {
        params: {
            shipment_id: id,
            port_name_from: from,
            port_name_to: to,
            departure_start: departure_start_int,
            departure_end: departure_end_int,
            restrict_product_id: prod_id,
            status: status,
            sort_by: sort,
            sort_ascending: sort_ascending,
            page: page,

        },
        validateStatus: function (status) {
            return status >= 200 && status <= 500
        }
    })

    if (resp.status !== 200) {
        alert("Cannot fetch shipments. Error: " + resp.status)
    } else {
        return resp.data
    }
}

function clear_filters() {
    document.getElementById("shipment-id").value = ""
    document.getElementById("loc-from").value = ""
    document.getElementById("loc-to").value = ""
    document.getElementById("export-date").value = ""
    document.getElementById("sort-by").value = "sort-default"
    document.getElementById("sort-direction").value = "ascending"



    handle_fetch_shipments()

}

async function handle_fetch_shipments() {
//     get inputs
    let shipment_id = document.getElementById("shipment-id").value
    let from = document.getElementById("loc-from").value
    let to = document.getElementById("loc-to").value
    let departure_start = document.getElementById("export-date").value.split(" - ")[0]
    let departure_end = document.getElementById("export-date").value.split(" - ")[1]
    let status = document.getElementById("status").value
    let prod_type = document.getElementById("export-type").value
    let sort_by = document.getElementById("sort-by").value
    let sort_ascending =document.getElementById("sort-direction").value === "ascending"

    let departure_start_int = new Date(departure_start + "T00:00").getTime()
    let departure_end_int = new Date(departure_end + "T23:59:59").getTime()

    if (Number.isNaN(departure_start_int)) {
        departure_start_int = undefined
    }

    if (Number.isNaN(departure_end_int)) {
        departure_end_int = undefined
    }

    const r = await fetch_shipments(shipment_id, from, to, departure_start_int, departure_end_int, prod_type, status, sort_by, sort_ascending, page)
    console.log(r)
    show_shipments(r)
}

debounce_timer_id = undefined
async function debounce_search() {
    if (debounce_timer_id !== undefined) {
        clearTimeout(debounce_timer_id)
        debounce_timer_id = undefined
    }

    debounce_timer_id = setTimeout(async() => {
        await handle_fetch_shipments()
    }, 150)

}

document.addEventListener("DOMContentLoaded", async() => {
    departure_date_picker = new Litepicker({
        element: document.getElementById("export-date"),
        mobileFriendly: true,
        format: "YYYY-MM-DD",
        singleMode: false,
        useResetBtn: true,
        buttonText: {
            reset: "Reset"
        },
    })

    const url_params = new URLSearchParams(window.location.search)
    if (url_params.get("prod_id") != null) {
        prod_id = parseInt(url_params.get("prod_id"))
    }
    if (url_params.get("batch_exp") != null) {
        batch_exp_date = parseInt(url_params.get("batch_exp"))
    }

    if (url_params.get("batch_id") != null) {
        batch_id = parseInt(url_params.get("batch_id"))
    }

    console.log(prod_id, batch_exp_date, batch_id)

    let port_from = document.getElementById("loc-from")

    // Autofocus on port_from
    port_from.focus()

    await handle_fetch_shipments()
})

