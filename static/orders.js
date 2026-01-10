

        let port_name_list = ["AA"]
        let produce_types = ["a"]

        document.addEventListener("DOMContentLoaded", () => {
            let departure_date_picker = new Litepicker({
                element: document.getElementById("export-date"),
                mobileFriendly: true,
                format: "YYYY-MM-DD",
                singleMode: true,
                useResetBtn: true,
                buttonText: {
                    reset: "Reset"
                },
            })

            let port_from = document.getElementById("loc-from")

            // Autofocus on port_from

            port_from.focus()


        })

