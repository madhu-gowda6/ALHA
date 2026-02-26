class UploadService {
  // stub — implemented in Epic 3
  Future<String?> getPresignedUrl(String sessionId) async => null;
  Future<bool> uploadImage(String presignedUrl, List<int> bytes) async => false;
}
