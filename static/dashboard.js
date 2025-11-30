async function logout() {
    let d = await axios.delete("/api/users/revoke-session")

    if (d.status === 200) {

        window.location.href = "login.html"
    } else {
        alert(`Cannot log out. (${d.status})`)
    }
}