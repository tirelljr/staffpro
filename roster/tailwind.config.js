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
					navy: "#16678C",
					teal: "#16678C",
					cyan: "#11A5DD",
					lime: "#90BA93",
					ink: "#111111",
					black: "#000000",
					lightCyan: "#A7C8CC",
				},
			},
		},
	},
	plugins: [],
};
