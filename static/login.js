async function run_login_flow() {
//     Get user credentials from input

    id_input = document.getElementById("username").value
    password_input = document.getElementById("password").value

    if (id_input.length === 0 || password_input.length === 0) {
        alert("Username and/or password is missing.")

    } else {
        let r = await axios.post("/session", {
            username: id_input,
            password: password_input
        })
        console.log("reached", r)
        if (r.status === 200) {
            console.log("reached")
            window.location.href = "/static/dashboard.html"
        } else if (r.status === 401) {
            alert("Wrong username or password!")
        }
    }
}

function toggle_password_visibility() {
    let e = document.getElementById("password")
    let d = document.getElementById("show-password-toggle")

    e.type = e.type == "password" ? "text" : "password"
    d.innerText = e.type == "password" ? "Show" : "Hide"
}

addEventListener("DOMContentLoaded", async (ev)=>{
    a = await axios.get("/api/users/check-logon")
    if (a.status === 200) {
        window.location.href = "/static/dashboard.html"
    }
})
