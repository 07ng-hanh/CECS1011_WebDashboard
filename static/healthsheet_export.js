function toggle_export_prompt(show) {
    if (show) {
        document.getElementById("export-recordings-prompt").style.display = "flex"
    } else {
        document.getElementById("export-recordings-prompt").style.display = "none"
    }
}

let export_range = undefined

async function request_sensor_recordings() {
    let date_from = export_range.getStartDate()
    date_from.setHours(0, 0, 0, 0)
    let date_to = export_range.getEndDate()
    date_to.setHours(23, 59, 59, 0)
    let file_format = document.getElementById("file-format").value
    date_to.setHours(23, 59, 59)
    date_from.setHours(23, 59, 59)
    console.log(date_from.getTime(), date_to.getTime())

    if (Number.isNaN(date_from.getTime()) || Number.isNaN(date_to.getTime())) {
        alert("Invalid date input. Date must not be empty.")
        return
    }

    if (date_from.getTime() > date_to.getTime()) {
        alert("Invalid date input. Start date must not be later than end date.")
        return
    }

    let resp = await axios.get("/api/sensors/export-recordings", {
        responseType: "blob",
        params: {
            from_timestamp_ms: date_from.getTime(),
            to_timestamp_ms: date_to.getTime(),
            file_format: file_format,
            utc_offset_minutes: new Date().getTimezoneOffset()
        }
    })

    if (resp.status === 200) {
        const blob_url = URL.createObjectURL(resp.data)
        const anchor_elem = document.createElement('a')
        anchor_elem.href = blob_url
        anchor_elem.download = `Sensor Export ${new Date().toString()}.${file_format}`
        anchor_elem.click()
        URL.revokeObjectURL(blob_url)

    } else {
        alert("Failed to export sensor recordings. Error " + resp.status)
    }

}

document.addEventListener("DOMContentLoaded", () => {
    // Inject litepicker for picking export time range
    export_range = new Litepicker({
        element: document.getElementById("date-range"),
        mobileFriendly: true,
        // format: "YYYY-MM-DD",
        singleMode: false,
        useResetBtn: true,
        buttonText: {
            reset: "Reset"
        },
    })


})