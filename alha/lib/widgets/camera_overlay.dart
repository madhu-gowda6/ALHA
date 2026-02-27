import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../providers/camera_provider.dart';
import '../services/upload_service.dart';

class CameraOverlay extends ConsumerStatefulWidget {
  final String sessionId;
  final String authToken;
  final String language;
  final void Function(String s3Key) onImageUploaded;
  final void Function() onAnalyzingMessage;

  const CameraOverlay({
    super.key,
    required this.sessionId,
    required this.authToken,
    required this.language,
    required this.onImageUploaded,
    required this.onAnalyzingMessage,
  });

  @override
  ConsumerState<CameraOverlay> createState() => _CameraOverlayState();
}

class _CameraOverlayState extends ConsumerState<CameraOverlay> {
  final _uploadService = UploadService();
  final _picker = ImagePicker();
  bool _isUploading = false;
  String? _errorMsg;

  Future<void> _pickAndUpload(ImageSource source) async {
    final xFile = await _picker.pickImage(source: source, imageQuality: 85);
    if (xFile == null) return;

    setState(() {
      _isUploading = true;
      _errorMsg = null;
    });
    ref.read(cameraProvider.notifier).setUploading(true);

    try {
      final bytes = await xFile.readAsBytes();

      final result = await _uploadService.getPresignedUrl(
          widget.sessionId, widget.authToken);

      ref.read(cameraProvider.notifier).setUploadProgress(0.5);

      await _uploadService.uploadImage(result.uploadUrl, bytes);

      ref.read(cameraProvider.notifier)
        ..setLastS3Key(result.s3Key)
        ..setImageBytes(result.s3Key, bytes)
        ..setUploading(false)
        ..setUploadProgress(1.0);

      if (mounted) Navigator.of(context).pop();
      widget.onAnalyzingMessage();
      widget.onImageUploaded(result.s3Key);
    } on UploadException catch (e) {
      ref.read(cameraProvider.notifier).setUploading(false);
      setState(() {
        _isUploading = false;
        _errorMsg =
            widget.language == 'hi' ? e.messageHi : e.message;
      });
    } catch (e) {
      ref.read(cameraProvider.notifier).setUploading(false);
      setState(() {
        _isUploading = false;
        _errorMsg = widget.language == 'hi'
            ? 'अपलोड विफल। कृपया पुनः प्रयास करें।'
            : 'Upload failed. Please try again.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 16),
            // Show both languages — farmers may be bilingual
            const Text(
              'कृपया जानवर की फोटो लें\nPlease take a photo of the animal',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 24),
            if (_isUploading)
              const Column(
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 12),
                  Text('Uploading... / अपलोड हो रहा है...'),
                ],
              )
            else ...[
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _PickerButton(
                    icon: Icons.camera_alt,
                    label: widget.language == 'hi' ? 'कैमरा' : 'Camera',
                    onTap: () => _pickAndUpload(ImageSource.camera),
                  ),
                  _PickerButton(
                    icon: Icons.photo_library,
                    label: widget.language == 'hi' ? 'गैलरी' : 'Gallery',
                    onTap: () => _pickAndUpload(ImageSource.gallery),
                  ),
                ],
              ),
              if (_errorMsg != null) ...[
                const SizedBox(height: 12),
                Text(
                  _errorMsg!,
                  style: const TextStyle(color: Colors.red, fontSize: 13),
                  textAlign: TextAlign.center,
                ),
              ],
            ],
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

class _PickerButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _PickerButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) => ElevatedButton.icon(
        onPressed: onTap,
        icon: Icon(icon),
        label: Text(label),
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        ),
      );
}
