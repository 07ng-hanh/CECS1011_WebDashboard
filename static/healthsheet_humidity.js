let humidity_chart = undefined
let humidity_readings = []
let humidity_streaming_duration_ms =  60 * 1000

// function update_chart()

let humidity_chart_cfg_liveUpdate = {
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
                realtime: {duration: humidity_streaming_duration_ms,}
            },
        },
        plugins: {
            streaming: {duration: humidity_streaming_duration_ms}
        }
    }}

let humidity_chart_cfg_static = {
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

function h_set_chart_duration_secs(d) {
    humidity_chart.destroy()

    if (d <= 3600) {
        h_create_polling_chart(d)
    //     Set up SSE polling here
    } else {
        h_create_static_chart(d)

    }
}

function h_define_chart_defaults() {
    Chart.defaults.font.size = 16
    Chart.defaults.font.fontColor = 'rgb(0,0,0)'
    Chart.defaults.responsive = true
    Chart.defaults.maintainAspectRatio = false
    Chart.defaults.plugins.legend.display = false
    Chart.defaults.plugins.tooltip.mode = 'index'
    Chart.defaults.plugins.tooltip.intersect = false
    Chart.defaults.datasets.spanGaps = false
}

function h_create_polling_chart(duration_s) {
    let humidity_chart_ctx = document.getElementById("humidity-plot")
    humidity_chart = new Chart(humidity_chart_ctx, humidity_chart_cfg_liveUpdate)
    humidity_chart.config.data.datasets[0].borderColor = 'rgb(31,122,255)'
    humidity_chart.config.options.scales.x.realtime.duration = duration_s * 1000

}

function h_create_static_chart(duration_s) {
    let humidity_chart_ctx = document.getElementById("humidity-plot")
    humidity_chart = new Chart(humidity_chart_ctx, humidity_chart_cfg_static)
    humidity_chart.config.data.datasets[0].borderColor = 'rgb(31,122,255)'
    humidity_chart.config.options.scales.x.min = Date.now() - duration_s * 1000
    humidity_chart.config.options.scales.x.max = Date.now()
    humidity_chart.options.plugins.decimation.enabled = true
    humidity_chart.options.plugins.decimation.algorithm = 'lttb'
    humidity_chart.options.plugins.decimation.threshold = 1


    humidity_chart.update()
    console.log(humidity_chart.config.options.scales.x.max - humidity_chart.config.options.scales.x.min)

}

document.addEventListener("DOMContentLoaded", () => {
    h_define_chart_defaults()
    h_create_polling_chart(60)
    document.getElementById("date-range-for-recordings").addEventListener("change", (ev) => {
        console.log(typeof(ev.target.value))
        h_set_chart_duration_secs( parseInt(ev.target.value))
    })

})
