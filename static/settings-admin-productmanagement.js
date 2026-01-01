function loadDataOntoProduceEditModal(name, temp_from, temp_to, co2_from, co2_to, humidity_from, humidity_to, lifespan) {

}

function toggleProduceEditModal(visible) {

    document.getElementById("editor-item-name").value = ""

    document.getElementById("edit-threshold-co2-to").value = ""
    document.getElementById("editor-item-threshold-co2-from").value = ""

    document.getElementById("edit-threshold-temp-to").value = ""
    document.getElementById("editor-item-threshold-temp-from").value = ""

    document.getElementById("edit-threshold-humidity-to").value = ""
    document.getElementById("editor-item-threshold-humidity-from").value = ""

    document.getElementById("editor-item-lifespan").value = ""

    if (visible === true) {
        document.getElementById("editor-item-modal").style.display = "flex"
        document.getElementById("editor-item-name").focus()

    } else {
        document.getElementById("editor-item-modal").style.display = "none"
    }
}

async function uploadProduceInfo(name, temp_from, temp_to, co2_from, co2_to, humidity_from, humidity_to, lifespan) {

    if (Number.isNaN(temp_from)) {
        temp_from = Number.NEGATIVE_INFINITY;
    }
    if (Number.isNaN(temp_to)) {
        temp_to = Number.POSITIVE_INFINITY;
    }
    if (Number.isNaN(co2_from)) {
        co2_from = Number.NEGATIVE_INFINITY;
    }
    if (Number.isNaN(co2_to)) {
        co2_to = Number.POSITIVE_INFINITY;
    }
    if (Number.isNaN(humidity_from)) {
        humidity_from = Number.NEGATIVE_INFINITY;
    }
    if (Number.isNaN(humidity_to)) {
        humidity_to = Number.POSITIVE_INFINITY;
    }


    let d = await axios.post("/admin/add-produce", {
        harvest_type_name: name,
        shelf_life: lifespan,
        thresh_temp_lo: temp_from,
        thresh_temp_hi: temp_to,
        thresh_co2_lo: co2_from,
        thresh_co2_hi: co2_to,
        thresh_humidity_lo: humidity_from,
        thresh_humidity_hi: humidity_to
    },  {
            validateStatus: function (status) {
                return status >= 200 && status <= 500
            }
        })

    return d.status
}

async function promptUploadProduceInfo() {
    let name = document.getElementById("editor-item-name").value.trim()
    let shelf_life = parseInt(document.getElementById("editor-item-lifespan").value.trim())
    let thresh_temp_lo = parseFloat(document.getElementById("editor-item-threshold-temp-from").value.trim())
    let thresh_temp_hi = parseFloat(document.getElementById("edit-threshold-temp-to").value.trim())
    let thresh_co2_lo = parseFloat(document.getElementById("editor-item-threshold-co2-from").value.trim())
    let thresh_co2_hi = parseFloat(document.getElementById("edit-threshold-co2-to").value.trim())
    let thresh_humidity_lo = parseFloat(document.getElementById("editor-item-threshold-humidity-from").value.trim())
    let thresh_humidity_hi = parseFloat(document.getElementById("edit-threshold-humidity-to").value.trim())

    if (Number.isNaN(shelf_life) || name === "") {
        alert("Name and/or Expected Shelf Life cannot be empty.")
        return
    }

    let responseCode = await uploadProduceInfo(
        name,
        thresh_temp_lo,
        thresh_temp_hi,
        thresh_co2_lo,
        thresh_co2_hi,
        thresh_humidity_lo,
        thresh_humidity_hi,
        shelf_life
    )

    if (responseCode !== 200) {
        alert(`Operation failed with exit code ${responseCode}`)
    } else {
        toggleProduceEditModal(false)
        await getAndShowProduceList(produce_page)
    }
}

let produce_page = 1
let produce_lim = 50
let produce_query = ""
async function getAndShowProduceList(page) {
    if (page < 1) {
        page = 1
    }
    produce_page = page
    console.log(produce_page)



    ret = await axios.get("/api/produce/list-produces", {
        validateStatus: function (status) {
                return status >= 200 && status <= 500
        },
        params: {
                page: produce_page,
                limit: produce_lim,
                query: produce_query
        }
    })

    if (ret.status === 200) {
        await showProduceList(ret.data)
    } else {
        alert("Loading produces failed.")
    }

}

async function showProduceList(produces) {
    // Show produces on the grid
    let tbl = document.querySelector("#produce-table tbody")
    console.log(tbl)
    tbl.innerHTML = ""

    document.querySelector("#page-produce").innerText = produce_page

    produces.forEach((value, index) => {
        let rowId = value[0]
        let shownId = index+1
        let rowData = value[1]
        let tblRow = document.createElement("tr")
        let idCell = document.createElement("td")
        let nameCell =  document.createElement("td")
        let shelfLifeCell =  document.createElement("td")
        let tempRangeCell =  document.createElement("td")
        let humidityRangeCell = document.createElement("td")
        let co2RangeCell = document.createElement("td")
        let actionCell= document.createElement("td")

        actionCell.className = "action-cell"
        // Action buttons
        let actionEdit = document.createElement("button")
        actionEdit.className = "sm"
        actionEdit.innerText = "Edit"

        let actionDelete = document.createElement("button")
        actionDelete.className = "sm danger"
        actionDelete.innerText = "Delete"
        actionDelete.addEventListener("click",  async() => {
           await promptDeleteProduct(rowId)
        })

        idCell.innerText = shownId
        nameCell.innerText = rowData.harvest_type_name
        shelfLifeCell.innerText = rowData.shelf_life
        tempRangeCell.innerHTML = `${rowData.thresh_temp_lo} ~ ${rowData.thresh_temp_hi}`
        humidityRangeCell.innerHTML = `${rowData.thresh_humidity_lo} ~ ${rowData.thresh_humidity_hi}`
        co2RangeCell.innerHTML = `${rowData.thresh_co2_lo} ~ ${rowData.thresh_co2_hi}`

        actionCell.appendChild(actionEdit)
        actionCell.appendChild(actionDelete)

        tblRow.appendChild(idCell)
        tblRow.appendChild(nameCell)
        tblRow.appendChild(shelfLifeCell)
        tblRow.appendChild(tempRangeCell)
        tblRow.appendChild(humidityRangeCell)
        tblRow.appendChild(co2RangeCell)
        tblRow.appendChild(actionCell)

        tbl.appendChild(tblRow)

    })
}

async function promptDeleteProduct(produceId) {
    if (confirm("Delete product?")) {
        ret = await axios.delete("/admin/delete-produce", {
            validateStatus: function (status) {
                return status >= 200 && status <= 500
            },
            params: {
                produceId: produceId
            }
        })

        if (ret.status !== 200) {
            alert("Can't delete produce entry. There are still batches of this produce in the warehouse database.")
        } else {
            alert("Operation successful.")
            getAndShowProduceList(produce_page)
        }
    }
}

async function queryProduce() {
    produce_query = document.getElementById("search-prod").value
    console.log("QUERY", produce_query)
    produce_page = 1
    getAndShowProduceList(produce_page)
}


let produce_search_debounce_id = undefined
document.addEventListener("DOMContentLoaded", async() => {
    getAndShowProduceList(1)

    document.querySelector("#search-prod").addEventListener("input", () => {
        if (produce_search_debounce_id !== undefined) {
            clearTimeout(produce_search_debounce_id)
        }
        produce_search_debounce_id = setTimeout(() => {
            queryProduce()
        }, 300)
    })
})