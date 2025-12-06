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
    } else {
        document.getElementById("editor-item-modal").style.display = "none"
    }
}

function uploadProduceInfo() {
    
}