let temp_chart = undefined
let temp_readings = []
let streaming_duration_ms =  60 * 1000

// function update_chart()

let chart_cfg_liveUpdate = {
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
                realtime: {duration: streaming_duration_ms,}
            },
        },
        plugins: {
            streaming: {duration: streaming_duration_ms}
        }
    }}

let chart_cfg_static = {
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

function set_chart_duration_secs(d) {
    temp_chart.destroy()

    if (d <= 3600) {
        create_polling_chart(d)
    //     Set up SSE polling here
    } else {
        create_static_chart(d)

    }
}

function define_chart_defaults() {
    Chart.defaults.font.size = 16
    Chart.defaults.font.fontColor = 'rgb(0,0,0)'
    Chart.defaults.responsive = true
    Chart.defaults.maintainAspectRatio = false
    Chart.defaults.plugins.legend.display = false
    Chart.defaults.plugins.tooltip.mode = 'index'
    Chart.defaults.plugins.tooltip.intersect = false
    Chart.defaults.datasets.spanGaps = false
}

function create_polling_chart(duration_s) {
    let temp_chart_ctx = document.getElementById("temperature-plot")
    temp_chart = new Chart(temp_chart_ctx, chart_cfg_liveUpdate)
    temp_chart.config.data.datasets[0].borderColor = 'rgb(136,94,255)'
    temp_chart.config.options.scales.x.realtime.duration = duration_s * 1000

}

function create_static_chart(duration_s) {
    let temp_chart_ctx = document.getElementById("temperature-plot")
    temp_chart = new Chart(temp_chart_ctx, chart_cfg_static)
    temp_chart.config.data.datasets[0].borderColor = 'rgb(136,94,255)'
    temp_chart.config.options.scales.x.min = Date.now() - duration_s * 1000
    temp_chart.config.options.scales.x.max = Date.now()
    temp_chart.options.plugins.decimation.enabled = true
    temp_chart.options.plugins.decimation.algorithm = 'lttb'
    temp_chart.options.plugins.decimation.threshold = 1


    temp_chart.update()
    console.log(temp_chart.config.options.scales.x.max - temp_chart.config.options.scales.x.min)

}

document.addEventListener("DOMContentLoaded", () => {
    define_chart_defaults()
    create_polling_chart(60)
    document.getElementById("date-range-for-recordings").addEventListener("change", (ev) => {
        console.log(typeof(ev.target.value))
        set_chart_duration_secs( parseInt(ev.target.value))
    })

})
