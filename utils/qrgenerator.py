import qrcode

qr = qrcode.QRCode(
    version=2,
    error_correction = qrcode.constants.ERROR_CORRECT_H,
    box_size=5,
    border=2
)
qr.add_data(779355097)
img = qr.make_image(fit=True)
img.show()