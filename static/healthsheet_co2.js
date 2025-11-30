let co2_chart = undefined
let co2_readings = []
let co2_streaming_duration_ms =  60 * 1000

// function update_chart()

let co2_chart_cfg_liveUpdate = {
    type: 'line',
    data: {
        datasets: [{
            pointRadius: 0,
            indexAxis: 'x',
            data: [[Date.now(), 10], [Date.now()+10000, 20], [Date.now()+20000, 10], [Date.now()+30000, 15], [Date.now()+40000, 10]] // push data in the form of [utc_timestamp_ms, sensor_reading] here
        }]
    },
    options: {

        scales: {
            x: {
                type: 'realtime',
                realtime: {duration: co2_streaming_duration_ms,}
            },
        },
        plugins: {
            streaming: {duration: co2_streaming_duration_ms}
        }
    }}

let co2_chart_cfg_static = {
    type: 'line',
    data: {
        datasets: [{
            pointRadius: 0,
            indexAxis: 'x',
            data: [[Date.now(), 10], [Date.now()+10000, 20], [Date.now()+20000, 10], [Date.now()+30000, 15], [Date.now()+40000, 10]], // push data in the form of [utc_timestamp_ms, sensor_reading] here
        }]
    },
    options: {

        scales: {
            x: {
                type: 'time',
            },
        },

    }}

function co2_set_chart_duration_secs(d) {
    co2_chart.destroy()

    if (d <= 3600) {
        co2_create_polling_chart(d)
    //     Set up SSE polling here
    } else {
        co2_create_static_chart(d)

    }
}

function co2_define_chart_defaults() {
    Chart.defaults.font.size = 16
    Chart.defaults.font.fontColor = 'rgb(0,0,0)'
    Chart.defaults.responsive = true
    Chart.defaults.maintainAspectRatio = false
    Chart.defaults.plugins.legend.display = false
    Chart.defaults.plugins.tooltip.mode = 'index'
    Chart.defaults.plugins.tooltip.intersect = false
    Chart.defaults.datasets.spanGaps = false
}

function co2_create_polling_chart(duration_s) {
    let co2_chart_ctx = document.getElementById("co2-plot")
    co2_chart = new Chart(co2_chart_ctx, co2_chart_cfg_liveUpdate)
    co2_chart.config.data.datasets[0].borderColor = 'rgb(41,169,0)'
    co2_chart.config.options.scales.x.realtime.duration = duration_s * 1000

}

function co2_create_static_chart(duration_s) {
    let co2_chart_ctx = document.getElementById("co2-plot")
    co2_chart = new Chart(co2_chart_ctx, co2_chart_cfg_static)
    co2_chart.config.data.datasets[0].borderColor = 'rgb(41,169,0)'
    co2_chart.config.options.scales.x.min = Date.now() - duration_s * 1000
    co2_chart.config.options.scales.x.max = Date.now()
    co2_chart.options.plugins.decimation.enabled = true
    co2_chart.options.plugins.decimation.algorithm = 'lttb'
    co2_chart.options.plugins.decimation.threshold = 1


    co2_chart.update()
    console.log(co2_chart.config.options.scales.x.max - co2_chart.config.options.scales.x.min)

}

document.addEventListener("DOMContentLoaded", () => {
    co2_define_chart_defaults()
    co2_create_polling_chart(60)
    document.getElementById("date-range-for-recordings").addEventListener("change", (ev) => {
        console.log(typeof(ev.target.value))
        co2_set_chart_duration_secs( parseInt(ev.target.value))
    })

})
