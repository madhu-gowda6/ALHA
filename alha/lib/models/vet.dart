class Vet {
  final String vetId;
  final String name;
  final String phone;
  final String speciality;
  final double lat;
  final double lon;
  final String district;
  final String state;

  const Vet({
    required this.vetId,
    required this.name,
    required this.phone,
    required this.speciality,
    required this.lat,
    required this.lon,
    required this.district,
    required this.state,
  });

  factory Vet.fromJson(Map<String, dynamic> json) => Vet(
        vetId: json['vet_id'] as String,
        name: json['name'] as String,
        phone: json['phone'] as String,
        speciality: json['speciality'] as String,
        lat: (json['lat'] as num).toDouble(),
        lon: (json['lon'] as num).toDouble(),
        district: json['district'] as String,
        state: json['state'] as String,
      );
}
