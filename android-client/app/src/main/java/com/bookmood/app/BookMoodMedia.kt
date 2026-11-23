package com.bookmood.app

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.qrcode.QRCodeWriter
import java.net.HttpURLConnection
import java.net.URI
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
internal fun PrototypeLayout.cover(
    title: String, author: String, url: String?, color: Color,
    x: Int, y: Int, large: Boolean
) {
    val width = if (large) 250 else 164
    val height = if (large) 360 else 218
    val radius = if (large) 8 else 10
    val bitmap by produceState<Bitmap?>(null, url) {
        value = null
        if (url != null) value = withContext(Dispatchers.IO) { downloadCover(url) }
    }
    val image = bitmap
    if (image != null) {
        Image(
            image.asImageBitmap(), "$title 표지",
            position(x, y, width, height).clip(RoundedCornerShape(units(radius))),
            contentScale = ContentScale.Fit
        )
    } else {
        surface(x, y, width, height, color, radius)
        surface(x + if (large) 11 else 14, y, 3, height, Palette.Sage)
        val dot = if (large) 62 else 41
        ellipse(x + if (large) 132 else 87, y + if (large) 50 else 31, dot, dot, Palette.Sage)
        val inset = if (large) 20 else 27
        label(title, x + inset, y + if (large) 140 else 85, width - inset - 10,
            if (large) 124 else 75, if (large) 37 else 24, Palette.Cream, true, lines = 2)
        label(author, x + inset, y + if (large) 292 else 177, width - inset - 8,
            if (large) 50 else 34, if (large) 23 else 15, Palette.Cream, lines = 2)
    }
}

@Composable
internal fun PrototypeLayout.musicQr(url: String, x: Int, y: Int, dimension: Int, onVisible: () -> Unit) {
    val bitmap by produceState<Bitmap?>(null, url) {
        value = withContext(Dispatchers.Default) {
            runCatching { encodeQr(url) }.getOrNull()
        }
    }
    val image = bitmap
    if (image != null) {
        val inset = 25
        Image(
            image.asImageBitmap(), "휴대폰으로 스캔하는 음악 QR 코드",
            position(x + inset, y + inset, dimension - 2 * inset, dimension - 2 * inset),
            filterQuality = FilterQuality.None
        )
        LaunchedEffect(url, image) { onVisible() }
    } else {
        label("음악 QR", x, y + 118, dimension, 55, 31, Palette.Dark, true, TextAlign.Center)
    }
}

private fun encodeQr(url: String): Bitmap {
    // Keep four quiet-zone modules. Render at an integer module size before layout scaling.
    val matrix = QRCodeWriter().encode(url, BarcodeFormat.QR_CODE, 0, 0, mapOf(EncodeHintType.MARGIN to 4))
    val module = 8
    val side = matrix.width * module
    val colors = IntArray(side * side) { index ->
        if (matrix[(index % side) / module, (index / side) / module]) {
            android.graphics.Color.BLACK
        } else {
            android.graphics.Color.WHITE
        }
    }
    return Bitmap.createBitmap(colors, side, side, Bitmap.Config.ARGB_8888)
}

private fun downloadCover(url: String): Bitmap? = runCatching {
    val connection = URI(url).toURL().openConnection() as HttpURLConnection
    try {
        connection.connectTimeout = 4_000
        connection.readTimeout = 5_000
        connection.inputStream.use(BitmapFactory::decodeStream)
    } finally {
        connection.disconnect()
    }
}.getOrNull()

