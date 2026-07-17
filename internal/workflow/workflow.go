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
	return "User minta deploy app ke Cloudflare: " + description + "\n\nLANGKAH WAJIB:\n1. Panggil create_project untuk provisioning proyek.\n2. Tulis Worker code ke file lokal menggunakan write_file atau patch_file.\n3. Jalankan deploy_project atau cf_deploy sesuai target.\n4. Verifikasi URL hasil deploy menggunakan cf_verify bila URL tersedia.\n5. Berikan URL live dan hasil verifikasi.\nJangan mengirim kode inline ke deploy_project."
}

func tddPrompt(target, description string) string {
	return "Jalankan workflow TDD untuk target " + target + ": " + description + ".\n\nUrutan wajib: inspeksi struktur proyek, tulis atau perbarui test yang awalnya gagal, jalankan test untuk membuktikan gagal, implementasikan perubahan minimal, jalankan ulang test sampai hijau, lalu ringkas file yang berubah dan hasil test. Gunakan tools secara langsung; jangan hanya menjelaskan rencana."
}
