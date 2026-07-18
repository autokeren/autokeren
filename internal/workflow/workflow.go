package workflow

import (
	"fmt"
	"strings"
)

func Expand(input string) (string, bool, error) {
	parts := strings.Fields(input)
	if len(parts) == 0 {
		return input, false, nil
	}
	argument := strings.TrimSpace(strings.TrimPrefix(input, parts[0]))
	switch parts[0] {
	case "/deploy":
		if argument == "" {
			return "", true, fmt.Errorf("format: /deploy <deskripsi app>")
		}
		return deployPrompt(argument), true, nil
	case "/tdd":
		segments := strings.SplitN(argument, "|", 2)
		if len(segments) != 2 || strings.TrimSpace(segments[0]) == "" || strings.TrimSpace(segments[1]) == "" {
			return "", true, fmt.Errorf("format: /tdd <nama_file> | <deskripsi_fitur>")
		}
		return tddPrompt(strings.TrimSpace(segments[0]), strings.TrimSpace(segments[1])), true, nil
	case "/spec":
		if argument == "" || argument == "show" || argument == "progress" {
			return input, false, nil
		}
		if strings.HasPrefix(argument, "answer ") {
			return "Lanjutkan interview spesifikasi yang sedang berjalan. Jawaban pengguna: " + strings.TrimSpace(strings.TrimPrefix(argument, "answer ")) + ". Ajukan pertanyaan berikutnya yang paling penting, atau jika cukup jelaskan bahwa pengguna dapat menjalankan /spec generate.", true, nil
		}
		if argument == "generate" {
			return "Berdasarkan interview spesifikasi pada konteks percakapan ini, buat rencana implementasi yang konkret. Gunakan write_file untuk menyimpan plan.md dan technical-plan.md di root proyek. Setiap langkah harus dapat diuji dan memiliki kriteria selesai yang jelas.", true, nil
		}
		return "Mulai interview spesifikasi untuk permintaan berikut: " + argument + ". Ajukan maksimal lima pertanyaan paling penting tentang pengguna, batasan, data, UX, dan kriteria selesai. Jangan menulis implementasi dulu; tunggu jawaban dengan /spec answer <jawaban>.", true, nil
	default:
		return input, false, nil
	}
}

func deployPrompt(description string) string {
	return "User minta membuat dan mempublikasikan aplikasi melalui Autokeren: " + description + "\n\nLANGKAH WAJIB:\n1. Panggil scaffold_app untuk membuat struktur modular dan autokeren.app.json.\n2. Tulis atau patch fitur ke file modular yang tercantum dalam manifest; jangan membuat satu Worker raksasa.\n3. Jika menambah file baru, perbarui daftar files pada autokeren.app.json.\n4. Jalankan test atau verifikasi lokal yang relevan.\n5. Panggil publish_app setelah pengguna menyetujui permission publish.\n6. Ambil app_release_status dari release_id hasil publish sampai status ready, lalu laporkan URL live.\nUntuk alur pemula jangan gunakan cf_deploy atau deploy_project; keduanya hanya jalur advanced/legacy."
}

func tddPrompt(target, description string) string {
	return "Jalankan workflow TDD untuk target " + target + ": " + description + ".\n\nUrutan wajib: inspeksi struktur proyek, tulis atau perbarui test yang awalnya gagal, jalankan test untuk membuktikan gagal, implementasikan perubahan minimal, jalankan ulang test sampai hijau, lalu ringkas file yang berubah dan hasil test. Gunakan tools secara langsung; jangan hanya menjelaskan rencana."
}
