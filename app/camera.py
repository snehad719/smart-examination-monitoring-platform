import cv2
import os


# Create uploads folder if it does not exist
os.makedirs("uploads", exist_ok=True)


# Open the default camera
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera could not be opened.")
    exit()


print("Camera opened successfully!")
print("Press SPACE to capture photo.")
print("Press ESC to cancel.")


while True:

    success, frame = camera.read()

    if not success:
        print("Could not read camera.")
        break

    cv2.imshow("ExamGuard Camera", frame)

    key = cv2.waitKey(1) & 0xFF

    # SPACE key
    if key == 32:

        file_path = "uploads/candidate_photo.jpg"

        cv2.imwrite(file_path, frame)

        print("Photo captured successfully!")
        print("Saved at:", file_path)

        break

    # ESC key
    elif key == 27:

        print("Camera cancelled.")
        break


camera.release()
cv2.destroyAllWindows()