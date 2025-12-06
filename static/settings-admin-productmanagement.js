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
    }



}