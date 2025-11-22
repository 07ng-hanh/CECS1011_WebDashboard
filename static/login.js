function run_login_flow() {
//     Get user credentials from input
    id_input = document.getElementById("username").value
    password_input = document.getElementById("password").value
    alert(id_input + password_input)
}

function toggle_password_visibility() {
    let e = document.getElementById("password")
    let d = document.getElementById("show-password-toggle")

    e.type = e.type == "password" ? "text" : "password"
    d.innerText = e.type == "password" ? "Show" : "Hide"
}