/*
 * Copyright (C) 2025 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.android.colorfilltestapp;

import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import android.view.View;
import android.view.ViewGroup;

/** Main activity for the application. */
public class MainActivity extends AppCompatActivity {
    public static final String EXTRA_COLOR = "color";

    public MainActivity() {}

    /** Called with the activity is first created. */
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        View backgroundView = new View(this);
        backgroundView.setLayoutParams(
                new ViewGroup.LayoutParams(
                        ViewGroup.LayoutParams.FILL_PARENT, ViewGroup.LayoutParams.FILL_PARENT));
        setContentView(backgroundView);

        Intent intent = getIntent();
        if (intent != null && intent.hasExtra(EXTRA_COLOR)) {
            // Get the color as a string (e.g., "#RRGGBB" or "red")
            String colorString = intent.getStringExtra(EXTRA_COLOR);
            if (colorString != null) {
                if (!colorString.startsWith("#")) {
                    colorString = "#" + colorString;
                }
                int color = Color.parseColor(colorString);
                backgroundView.setBackgroundColor(color);
            }
        }
    }
}
