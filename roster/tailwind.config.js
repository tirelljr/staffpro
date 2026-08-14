import frappeUIPreset from "frappe-ui/src/tailwind/preset";
export default {
	presets: [frappeUIPreset],
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		"./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
		"../node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}",
	],
	theme: {
		extend: {
			colors: {
				brand: {
					navy: "#16607a",
					cyan: "#00a6e8",
					lime: "#8cc040",
					ink: "#1e3a4c",
					black: "#000000",
				},
			},
		},
	},
	plugins: [],
};
