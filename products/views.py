def processing(request):
    """
    Procesa la imagen subida por el usuario usando la vista seleccionada.
    """
    ensure_dirs()
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return render(request, "error.html", {"error": "Falta la clave de API de OpenAI."})

    try:
        # 🧠 Recuperamos información guardada en la sesión
        job_id = request.session.get("job_id")
        selection = request.session.get("selection")
        selected_view = request.session.get("selected_view")  # ⚡ Recuperamos la vista elegida
        uploaded_file_url = request.session.get("uploaded_file_url")

        if not uploaded_file_url:
            return render(request, "error.html", {"error": "No se encontró la imagen subida."})

        # Si no hay vista seleccionada, usar la 1 por defecto
        if not selected_view:
            selected_view = "1"

        # Validamos que selection sea un diccionario y tenga las claves esperadas
        if not isinstance(selection, dict):
            return render(request, "error.html", {"error": "Error interno: selección inválida."})

        categoria = selection.get("categoria", "")
        subcategoria = selection.get("subcategoria", "")

        # 🧩 Localizamos la carpeta correspondiente a la vista elegida
        base_path = Path(settings.LINEAS_ROOT) / f"{categoria} {subcategoria}".strip()
        assets_folder = base_path / selected_view

        if not assets_folder.exists():
            return render(
                request,
                "error.html",
                {"error": f"No se encontró la carpeta de la vista seleccionada ({selected_view})."},
            )

        # 🧩 Buscar archivos .txt y .png dentro de la carpeta
        txt_files = list(assets_folder.glob("*.txt"))
        png_files = list(assets_folder.glob("*.png"))

        if not txt_files or not png_files:
            return render(
                request,
                "error.html",
                {"error": "Faltan los archivos necesarios (.txt o .png) en la vista seleccionada."},
            )

        # 📝 Leemos el prompt del archivo .txt
        with open(txt_files[0], "r", encoding="utf-8") as f:
            prompt = f.read().strip()

        # 📸 Ruta de la imagen subida
        input_path = job_id if isinstance(job_id, str) else None
        if not input_path:
            input_path = uploaded_file_url

        # 🔍 Aseguramos que sea texto, no dict
        if isinstance(input_path, dict):
            input_path = input_path.get("path", "")

        input_path = str(Path(settings.MEDIA_ROOT) / uploaded_file_url.replace("/media/", ""))

        if not os.path.exists(input_path):
            return render(request, "error.html", {"error": "No se encontró la imagen subida en el servidor."})

        # Convertimos a RGBA si es necesario
        img = Image.open(input_path)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        rgba_path = str(Path(input_path).with_suffix(".png"))
        img.save(rgba_path, "PNG")
        input_path = rgba_path

        # 🔥 Llamada a OpenAI con la vista elegida
        client = OpenAI(api_key=api_key)
        with open(input_path, "rb") as image_file:
            response = client.images.edit(
                model="gpt-image-1",
                image=image_file,
                prompt=prompt,
                size="1024x1024"
            )

        # Guardamos la imagen generada
        image_url = response.data[0].url
        request.session["generated_image_url"] = image_url

        return render(
            request,
            "products/result.html",
            {
                "image_url": image_url,
                "selected_view": selected_view,
                "selection": selection,
            },
        )

    except Exception as e:
        logger.error(f"Error procesando imagen: {e}")
        return render(
            request,
            "error.html",
            {"error": f"Error al procesar la imagen: {str(e)}"},
        )
