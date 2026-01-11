document.addEventListener("DOMContentLoaded", async () => {
    // Drawing contexts
    let ctx_temperature = document.getElementById("temperature-plot")
    let ctx_co2 = document.getElementById("co2-plot")
    let ctx_humidity = document.getElementById("humidity-plot")

    let realtime_duration = parseInt(document.getElementById("date-range-for-recordings").value)
    // Chart Configuration
    const realtime_chart_config_common = {
        type: 'line',
        data: {
            datasets: [
                {data: [], borderColor: '#36A2EB', backgroundColor: '#36A2EB2E', pointRadius: 0}
            ]
        },
        options: {
            interaction: {
                intersect: false
            },
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'realtime',
                    realtime: {
                        duration: realtime_duration
                    }
                },
                y: {}
            },
            plugins: {
                decimation: {
                    enabled: false,
                }
            }
        },

    }

    const static_chart_config_common = {
        type: 'line',
        data: {
            datasets: [
                {data: [], borderColor: '#36A2EB', backgroundColor: '#36A2EB2E', pointRadius: 0}
            ]
        },
        options: {
            interaction: {
                intersect: false
            },
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time'
                },
                y: {}
            }
        },
    }

    chart_temperature = undefined
    chart_co2 = undefined
    chart_humidity = undefined

    function initCharts(span_ms) {
        // Reset chart
        if (chart_temperature !== undefined) {
            chart_temperature.data.datasets[0].data = []
            chart_temperature.destroy()
        }
        if (chart_co2 !== undefined) {
            chart_co2.data.datasets[0].data = []
            chart_co2.destroy()
        }
        if (chart_humidity !== undefined) {
            chart_humidity.data.datasets[0].data = []
            chart_humidity.destroy()
        }

        // Set chart type
        // Realtime
        let _base_chart_config = {}
        if (span_ms <= 3600000) {
            _base_chart_config = realtime_chart_config_common
            _base_chart_config.options.scales.x.realtime.duration = span_ms
        } else {
        //     TODO: static chart
            _base_chart_config = static_chart_config_common
        //     Set time span
            const time_now_ms = new Date().getTime()
            _base_chart_config.options.scales.x.min = time_now_ms - span_ms
            _base_chart_config.options.scales.x.max = time_now_ms
        }

        // Charts
        chart_temperature = new Chart(ctx_temperature, structuredClone(_base_chart_config))
        chart_temperature.config.options.scales.y.suggestedMin = -30
        chart_temperature.config.options.scales.y.suggestedMax = 30
        chart_co2 = new Chart(ctx_co2, structuredClone(_base_chart_config))
        chart_co2.config.options.scales.y.suggestedMin = 0
        chart_co2.config.options.scales.y.suggestedMax = 1000
        chart_humidity = new Chart(ctx_humidity, structuredClone(_base_chart_config))
        chart_humidity.config.options.scales.y.suggestedMin = 0
        chart_humidity.config.options.scales.y.suggestedMax = 100

    }

    async function fetchHistoricData(current_time_ms, span_ms, interval_ms) {
        let d = await axios.get("/api/sensors/sensor-data-historic-v2", {
            validateStatus: function (status) {
                return status >= 200 && status <= 500
            },
            params: {
                current_time_ms: current_time_ms,
                length_ms: span_ms,
                interval_ms: interval_ms
            }
        })

        if (d.status === 200) {
            // sort array in chronologically increasing order so the next elements (live-inserted) keeps the array monotonic
            // this way, the graph does not glitch out while trying to connect point n-1 to n
            d.data.sort((a, b) => a.timestamp - b.timestamp)
            console.log(d.data)
            d.data.forEach((v) => {
                chart_temperature.data.datasets[0].data.push(
                    {x: v.timestamp, y: v.temperature}
                )
                chart_co2.data.datasets[0].data.push(
                    {x: v.timestamp, y: v.co2}
                )
                chart_humidity.data.datasets[0].data.push(
                    {x: v.timestamp, y: v.humidity}
                )

            })
            chart_temperature.update('quiet')
            chart_co2.update('quiet')
            chart_humidity.update('quiet')
        } else {
            alert("Can't fetch historic data. Error " + d.status)
        }

    }

    let eventSrc = undefined
    function enableRealtimeReading(interval_ms) {
        if (eventSrc !== undefined) {
            eventSrc.close()
            eventSrc = undefined
        }
        // drop the first few SSE data point due to chartjs connector glitch

        eventSrc = new EventSource(`/api/sensors/sensor-data-stream?interval=${interval_ms}`)
        eventSrc.onmessage = (ev) => {
            const v = JSON.parse(ev.data)

            //     add data to chart

            console.log(v.timestamp)
            chart_temperature.data.datasets[0].data.push(
                {x: v.timestamp, y: v.temperature}
            )
            chart_co2.data.datasets[0].data.push(
                {x: v.timestamp, y: v.co2}
            )
            chart_humidity.data.datasets[0].data.push(
                {x: v.timestamp, y: v.humidity}
            )
            chart_temperature.update('quiet')
            chart_co2.update('quiet')
            chart_humidity.update('quiet')


        }
    }

    function clearChartData() {
        chart_temperature.data.datasets[0].data = []
        chart_co2.data.datasets[0].data = []
        chart_humidity.data.datasets[0].data = []

    }

    function disableRealtimeReading() {
        if (eventSrc !== undefined) {
            eventSrc.close()
            eventSrc = undefined
        }
    }

    // Update chart settings on timespan config change
    document.getElementById("date-range-for-recordings").addEventListener("change", async() => {
        realtime_duration = parseInt(document.getElementById("date-range-for-recordings").value)
        disableRealtimeReading()
        initCharts(realtime_duration)
        let interval_ms = 1000 // sample every sec

        if (realtime_duration >= 1800000) {
            interval_ms = 10000 // sample every 10 secs
        }
        if (realtime_duration >= 28800000) {
            interval_ms = 60000 // sample every 60 secs
        }
        await fetchHistoricData(new Date().getTime(), realtime_duration, interval_ms)

        if (realtime_duration <= 3600000) {
           enableRealtimeReading(interval_ms)

        }
    })

    document.getElementById("manual-refresh-btn").addEventListener("click", async() => {
        clearChartData()
        realtime_duration = parseInt(document.getElementById("date-range-for-recordings").value)
        let interval_ms = 1000 // sample every sec

        if (realtime_duration >= 1800000) {
            interval_ms = 10000 // sample every 10 secs
        }
        if (realtime_duration >= 28800000) {
            interval_ms = 60000 // sample every 60 secs
        }
        await fetchHistoricData(new Date().getTime(), realtime_duration, interval_ms)

    })

    initCharts(realtime_duration)
    await fetchHistoricData(new Date().getTime(), realtime_duration, 2000)
    if (realtime_duration <= 3600000) {
        enableRealtimeReading(1000)
    }


})