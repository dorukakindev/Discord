-# CODEX MYTHICA · Hiyeroglif Rehberi · Kayıt
# AI yanıtı kanıt tablosu üretir
> **Durum:** Panel içi AI, hiyeroglif fotoğrafı veya kullanıcı transkripsiyonu hakkında yorum yaparken. · **Notasyon:** claim / evidence / uncertainty / next source · **Çıktı Kalıbı:** İddia: ... | Kanıt: ... | Güven: ... | Eksik: ... | Sonraki kaynak: ... · **Risk:** AI'nin akıcı cevabını filolojik edisyon gibi göstermek.

### Adımlar
- Her iddiayı kanıt türüyle eşleştir: müze kaydı, korpus, edisyon, Unicode, eğitim kaynağı veya kullanıcı görseli.
- Eksik veri varsa çeviri yerine doğrulama planı üret.
- Kaynak pusulası katmanını kullanarak hangi iddianın hangi güven seviyesinde olduğunu yaz.
- Son satırda bir sonraki en iyi kaynak adımını ver.

### Kanıtlar
- Kaynak pusulası
- Karar ağacı
- Korpus rotası
- Kullanıcı girdisi

### Kaynak No
- HIEROGLYPH_SOURCE_CONFIDENCE_MATRIX
- HIEROGLYPH_READING_DECISION_TREE
- TLA - Text Corpus