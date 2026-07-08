# Laporan Masalah: `thought_signature` pada Gemini 3.5 (AI Studio)

## Deskripsi Masalah
Model Gemini 3.5 (khususnya `gemini-3.5-flash` dan `gemini-3.5-pro`) di Google AI Studio mengalami kegagalan saat menggunakan fitur *Function Calling* (Tools). API mengembalikan error HTTP 400 yang menyatakan bahwa `thought_signature` hilang, meskipun model itu sendiri yang menghasilkan pemanggilan fungsi tersebut.

## Detail Error
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent` (dan streaming)
- **Status Code**: 400 Bad Request
- **Pesan Error**:
```json
{
  "error": {
    "code": 400,
    "message": "Function call is missing a thought_signature in functionCall parts. This is required for tools to work correctly, and missing thought_signature may lead to degraded model performance. Additional data, function call `default_api:run_shell` , position 2. Please refer to https://ai.google.dev/gemini-api/docs/thought-signatures for more details.",
    "status": "INVALID_ARGUMENT"
  }
}
```

## Analisis Teknis
Berdasarkan dokumentasi [Gemini Thought Signatures](https://ai.google.dev/gemini-api/docs/thought-signatures), model tertentu mewajibkan adanya blok teks "pemikiran" sebelum blok `functionCall`.

Dalam pengujian kami:
1. **Model-Generated Call**: Saat model memutuskan untuk memanggil tool (misal: `list_files`), model memberikan respons yang berisi `functionCall` tetapi **tanpa** menyertakan `text` part (thought) sebelumnya. API kemudian menolak respons yang dihasilkan modelnya sendiri.
2. **Manual Injection**: Kami mencoba menyuntikkan `text` part secara manual ke dalam riwayat percakapan sebelum `functionCall` dikirim balik ke API, namun error tetap muncul dengan referensi "position 2", yang mengindikasikan ketidakkonsistenan pada urutan part yang diharapkan oleh server Gemini.

## Langkah Reproduksi
1. Gunakan model `gemini-3.5-flash` via AI Studio API.
2. Deklarasikan tool (misal: `run_shell` atau `list_files`).
3. Berikan prompt yang memicu penggunaan tool tersebut (misal: "tampilkan daftar file").
4. API akan mengembalikan error 400 segera setelah model mencoba memanggil fungsi tersebut.

## Upaya Perbaikan yang Sudah Dilakukan (Sisi Client)
- [x] Menambahkan `text` part manual sebelum `functionCall` dalam payload `contents`.
- [x] Menambahkan `text` part manual sebelum `functionResponse` saat mengirim hasil eksekusi tool.
- [x] Memastikan urutan part mengikuti pola: `text` (thought) -> `functionCall`.
- [x] Menghindari penggabungan part otomatis (*strict alternation*) untuk menjaga posisi `thought_signature`.

**Hasil**: Semua upaya di atas tetap menghasilkan error yang sama.

## Solusi yang Diterapkan
Karena `thought_signature` hanya diverifikasi oleh Gemini 3.5 pada **riwayat** `functionCall` (bukan saat model pertama kali memanggil tool), kita mengubah riwayat tool calls menjadi plain text sebelum mengirim ulang ke API.

Detail implementasi di `autokeren/models/aistudio.py`:
- Menambahkan `_is_thinking_model()` untuk mendeteksi Gemini 3.5/3.0.
- Menambahkan `_flatten_gemini_history()` yang mengubah pesan `role=assistant` dengan `tool_calls` dan pesan `role=tool` menjadi format teks:
  - `[TOOL_CALL name=...]\n{args}`
  - `[TOOL_RESULT name=...]\n{result}`
- Native function calling tetap digunakan pada turn saat model merespons, sehingga model masih bisa memilih tool secara terstruktur.
- Model non-thinking (Gemini 1.5) tetap menggunakan native `functionCall`/`functionResponse` karena tidak terkena masalah ini.

## Rekomendasi
- Melaporkan bug ini ke [Google AI Studio Issue Tracker](https://issuetracker.google.com/) tetap disarankan.
- Fallback ke Gemini 1.5 Pro/Flash tetap opsi yang aman.
- Pantau perilaku Gemini 3.5; jika Google memperbaiki validasi `thought_signature` di masa depan, native history bisa diaktifkan kembali.
# ak:1473650b05f687af
