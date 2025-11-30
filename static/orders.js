

        let port_name_list = ["AA"]
        let produce_types = ["a"]

        document.addEventListener("DOMContentLoaded", () => {
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

            let port_from = document.getElementById("loc-from")
            let port_to = document.getElementById("loc-to")
            let prod_type = document.getElementById("export-type")

            let port_from_autocomplete = new Awesomplete(port_from, {
                minChars: 0,
                maxItems: 15,
                list: port_name_list
            })
            port_from_autocomplete.evaluate()
            port_from_autocomplete.close()

            let port_to_autocomplete = new Awesomplete(port_to, {
                minChars: 0,
                maxItems: 15,
                list: port_name_list
            })
            port_to_autocomplete.evaluate()
            port_to_autocomplete.close()

            let export_produce_type_autocomplete = new Awesomplete(prod_type, {
                minChars: 0,
                maxItems: 15,
                list: produce_types
            })
            export_produce_type_autocomplete.evaluate()
            export_produce_type_autocomplete.close()

            port_from.addEventListener("focus", () => {
                port_from_autocomplete.open()
            })

            port_to.addEventListener("focus", () => {
                port_to_autocomplete.open()
            })

            prod_type.addEventListener("focus", () => {
                export_produce_type_autocomplete.open()
            })

            // Autofocus on port_from

            // port_from_autocomplete.open()
            port_from.focus()


        })

